using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
[DefaultExecutionOrder(200)] // run after typical movers
public class BoatFloatOnBulge : MonoBehaviour
{
    [Header("Refs")]
    public MoveBulge moveBulge;     // your existing MoveBulge on the water plane
    public Transform waterPlane;    // that same plane transform (for tilt sampling)

    [Header("Height")]
    public float waterYOffset = 0.2f;  // small lift above water surface
    public float maxRiseSpeed = 10f;   // clamp vertical speed (m/s) to prevent snapping
    public float heightDamping = 0.6f;  // 0..1 smoothing of vertical motion

    [Header("Optional tilt (pitch/roll only)")]
    public bool tiltToWater = true;
    [Range(0f, 20f)] public float maxTiltDeg = 12f;
    [Range(0f, 1f)] public float tiltLerp = 0.15f;
    public float tiltSampleEps = 0.5f;   // meters for gradient sampling

    Rigidbody rb;

    void Awake()
    {
        rb = GetComponent<Rigidbody>();
        // Keep the hull upright; your path follower controls yaw.
        rb.constraints |= RigidbodyConstraints.FreezeRotationX | RigidbodyConstraints.FreezeRotationZ;
    }

    void FixedUpdate()
    {
        if (!moveBulge) return;

        // --- 1) Target water height under the boat ---
        Vector3 pos = rb.position;
        float waterY = moveBulge.GetWaterHeightAtWorldXZ(pos.x, pos.z) + waterYOffset;

        // Smooth + clamp vertical motion so it never "flies"
        float dy = waterY - pos.y;
        float maxStep = maxRiseSpeed * Time.fixedDeltaTime;
        dy = Mathf.Clamp(dy, -maxStep, maxStep);
        pos.y += dy * (1f - heightDamping);   // apply damping
        rb.MovePosition(pos);

        // --- 2) Optional tilt from local water normal (pitch/roll only) ---
        if (tiltToWater && waterPlane)
        {
            float eps = tiltSampleEps;
            // sample heights around the boat in plane's local axes (world directions)
            Vector3 r = waterPlane.right * eps;
            Vector3 f = waterPlane.forward * eps;
            float hC = moveBulge.GetWaterHeightAtWorldXZ(pos.x, pos.z);
            float hR = moveBulge.GetWaterHeightAtWorldXZ(pos.x + r.x, pos.z + r.z);
            float hF = moveBulge.GetWaterHeightAtWorldXZ(pos.x + f.x, pos.z + f.z);

            // build a normal from the sampled slope (world)
            Vector3 vR = new Vector3(r.x, hR - hC, r.z);
            Vector3 vF = new Vector3(f.x, hF - hC, f.z);
            Vector3 n = Vector3.Cross(vF, vR).normalized;
            if (n.y < 0f) n = -n;

            // keep current yaw; only tilt toward the water normal
            Vector3 forwardFlat = Vector3.ProjectOnPlane(transform.forward, Vector3.up).normalized;
            Vector3 fwdOnPlane = Vector3.ProjectOnPlane(forwardFlat, n).normalized;
            if (fwdOnPlane.sqrMagnitude < 1e-4f) fwdOnPlane = Vector3.ProjectOnPlane(Vector3.forward, n).normalized;

            Quaternion target = Quaternion.LookRotation(fwdOnPlane, n);
            Quaternion flat = Quaternion.LookRotation(fwdOnPlane, Vector3.up);
            float tilt = Quaternion.Angle(flat, target);
            if (tilt > maxTiltDeg)
                target = Quaternion.Slerp(flat, target, maxTiltDeg / Mathf.Max(1e-3f, tilt));

            transform.rotation = Quaternion.Slerp(transform.rotation, target, tiltLerp);
        }
    }
}
