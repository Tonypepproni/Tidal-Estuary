using UnityEngine;

// make sure this runs AFTER MoveBulge each frame
[DefaultExecutionOrder(+20)]
[RequireComponent(typeof(Rigidbody))]
public class BoatFloat_Snap : MonoBehaviour
{
    public Transform waterPlane;   // the plane with MoveBulge on it
    public MoveBulge moveBulge;    // your existing script on water
    public float waterYOffset = 0.2f; // small lift above water
    public float bobAmplitude = 0.0f; // set >0 if you want idle bob
    public float bobFreq = 1.2f;

    Rigidbody rb;

    void Awake() { rb = GetComponent<Rigidbody>(); }

    void LateUpdate()
    {
        if (!waterPlane || !moveBulge) return;

        // WORLD -> LOCAL (relative to the water plane)
        Vector3 local = waterPlane.InverseTransformPoint(rb.position);

        // Gaussian like MoveBulge: y = H * exp(-r^2 / (2*sigma^2))
        float sigma = Mathf.Max(0.001f, moveBulge.radius * moveBulge.sharpness);

        // Crest center in LOCAL space: project your crest/wave marker to local XZ.
        // If you have a visible crest marker (e.g., "wavebar"), drag it here.
        // If not, approximate by using the boat’s local X, and the crest’s local Z from MoveBulge:
        // — If you don’t have a crest Z, skip this and use wavebar (Option 3 below).
        Vector3 crestLocal = moveBulge.transform.InverseTransformPoint(moveBulge.GetCrestWorldPos());

        float dx = local.x - crestLocal.x;
        float dz = local.z - crestLocal.z;
        float r2 = dx*dx + dz*dz;
        float bulgeY = moveBulge.height * Mathf.Exp(-r2 / (2f * sigma * sigma));

        // Base water plane world Y (important since you moved the plane below terrain)
        float baseY = waterPlane.TransformPoint(Vector3.zero).y;

        float targetY = baseY + bulgeY + waterYOffset
                        + (bobAmplitude > 0 ? Mathf.Sin(Time.time * bobFreq) * bobAmplitude : 0f);

        Vector3 p = rb.position; p.y = targetY;
        rb.MovePosition(p);  // only change Y; your path script handles XZ
    }
}
