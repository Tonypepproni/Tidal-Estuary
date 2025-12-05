using System.Collections.Generic;
using UnityEngine;

[ExecuteAlways]
public class WaveBarAlongPath : MonoBehaviour
{
    [Header("Path (same spheres you used for the bulge)")]
    public List<Transform> waypoints = new List<Transform>();
    public bool loop = true;
    public float speed = 5f;

    [Header("Bar look")]
    public float barLength = 6f;      // along path
    public float barWidth  = 2f;      // across river
    public float yOffset   = 0.05f;   // sit just above water
    public Material unlitWhite;       // Optional; script will make one if null

    [Header("Expose crest position for other scripts")]
    public Vector3 CrestWorldPos { get; private set; }

    MeshRenderer mr; MeshFilter mf;
    List<Vector3> wp = new(); List<float> sCum = new();
    float pathLen, s;

    void OnEnable()
    {
        EnsureQuad();
        RebuildPath();
    }

    void OnValidate() { RebuildPath(); ResizeQuad(); }

    void Update()
    {
        if (!Application.isPlaying && !enabled) return;

        if (wp.Count < 2) return;
        float dt = Application.isPlaying ? Time.deltaTime : 1f / 60f;

        s += speed * dt;
        if (loop) { if (s > pathLen) s -= pathLen; }
        else { s = Mathf.Min(pathLen, s); }

        var p  = EvalAt(s);
        var p2 = EvalAt(Mathf.Min(pathLen, s + barLength));
        var dir = (p2 - p); dir.y = 0f;
        var rot = dir.sqrMagnitude > 0.0001f ? Quaternion.LookRotation(dir.normalized, Vector3.up) : transform.rotation;

        CrestWorldPos = p;
        transform.SetPositionAndRotation(p + Vector3.up * yOffset, rot);
        ResizeQuad();
    }

    void EnsureQuad()
    {
        mf = GetComponent<MeshFilter>();
        mr = GetComponent<MeshRenderer>();
        if (!mf) mf = gameObject.AddComponent<MeshFilter>();
        if (!mr) mr = gameObject.AddComponent<MeshRenderer>();

        if (!mf.sharedMesh)
        {
            var q = GameObject.CreatePrimitive(PrimitiveType.Quad);
            var qm = q.GetComponent<MeshFilter>().sharedMesh;
            DestroyImmediate(q);
            mf.sharedMesh = Instantiate(qm);
        }
        if (!unlitWhite)
        {
            unlitWhite = new Material(Shader.Find("Unlit/Color"));
            unlitWhite.color = Color.white;
        }
        mr.sharedMaterial = unlitWhite;
        transform.localScale = new Vector3(barWidth, barLength, 1f); // Quad’s Y is “length” in its local space
        transform.rotation = Quaternion.Euler(90f, 0f, 0f); // make Quad lie flat initially
    }

    void ResizeQuad()
    {
        if (!mf) return;
        transform.localScale = new Vector3(barWidth, barLength, 1f);
    }

    void RebuildPath()
    {
        wp.Clear(); sCum.Clear(); pathLen = 0f;
        if (waypoints == null || waypoints.Count < 2) return;
        foreach (var t in waypoints) if (t) wp.Add(t.position);
        if (wp.Count < 2) return;

        sCum.Add(0f);
        for (int i = 1; i < wp.Count; i++)
        {
            pathLen += Vector3.Distance(wp[i - 1], wp[i]);
            sCum.Add(pathLen);
        }
        s = Mathf.Clamp(s, 0f, pathLen);
    }

    Vector3 EvalAt(float sVal)
    {
        if (sVal <= 0f) return wp[0];
        if (sVal >= pathLen) return wp[^1];
        int seg = 0;
        while (seg < sCum.Count - 1 && sCum[seg + 1] < sVal) seg++;
        float t = Mathf.InverseLerp(sCum[seg], sCum[seg + 1], sVal);
        return Vector3.Lerp(wp[seg], wp[seg + 1], t);
    }
}
