using System.Collections.Generic;
using UnityEngine;

/*To whom ever this may concern,
I wish you good luck. 
If you can decipher all this code I dont know how it ended up like this but 
it did. My name is Hector Eligio it is 12/7/25 I graduate from Pace University in 10 days, 
I created this whole project from top to bottom, it drove me insane. 
GodSpeed if you intend on working further on this project.*/

[ExecuteAlways]
[RequireComponent(typeof(MeshFilter))]
public class MoveBulge : MonoBehaviour
{
    [Header("Wave (local Y bulge)")]
    public float height = 2f;
    public float radius = 6f;
    [Range(0.05f, 1f)] public float sharpness = 0.35f;

    [Header("Path (drop your river spheres here in order)")]
    public List<Transform> waypoints = new List<Transform>();

    public enum TravelMode { Loop, PingPong, Once }
    public TravelMode travel = TravelMode.Loop;
    public float speed = 5f;                 // meters/second along the path
    public float waypointTolerance = 0.25f;

    [Header("Editor/Runtime")]
    public bool animateInEditMode = false;
    public bool recalcNormals = true;
    public Mesh originalPlaneMesh;

    // ---- internals ----
    MeshFilter _mf;
    Mesh _mesh;
    Vector3[] _base, _deformed;
    bool _madeEditorCopy;

    // polyline cache
    List<Vector3> _wpWorld = new();     // world positions
    List<float> _wpS = new();     // cumulative distances
    float _pathLen;
    float _s;                           // current distance along path
    int _dir = 1;                       // 1 forward, -1 back (PingPong)

    // cached crest (for helpers)
    Vector3 _crestLocal;   // on the plane, local space
    Vector3 _crestWorld;   // world space

    void OnEnable()
    {
        float dt = Time.deltaTime;

        // WebGL sometimes reports unstable delta time
#if UNITY_WEBGL
        dt *= 1.2f;   // smooth correction factor
#endif

        _mf = GetComponent<MeshFilter>();

        if (Application.isPlaying)
        {
            var src = _mf.sharedMesh;
            _mesh = Instantiate(src);
            _mesh.name = (src ? src.name : "Mesh") + " (Bulge Runtime)";
            _mf.sharedMesh = _mesh;
        }
        else
        {
            var src = _mf.sharedMesh;
            if (src)
            {
                _mesh = Instantiate(src);
                _mesh.name = src.name + " (Bulge Editor)";
                _mf.sharedMesh = _mesh;
                _madeEditorCopy = true;
            }
        }

        if (_mesh != null)
        {
            _base = _mesh.vertices;
            _deformed = new Vector3[_base.Length];
        }

        RebuildPathCache();
        _s = 0f; _dir = 1;
    }

    void OnDisable()
    {
        if (!Application.isPlaying && _madeEditorCopy && _mesh)
            DestroyImmediate(_mesh);
        _mesh = null; _base = null; _deformed = null;
    }

    void OnValidate()
    {
        radius = Mathf.Max(0.001f, radius);
        speed = Mathf.Max(0f, speed);
        RebuildPathCache();
    }

    void Update()
    {
        if (_mesh == null || _base == null) return;
        if (!Application.isPlaying && !animateInEditMode) return;
        if (_pathLen <= 0.001f) return;

        float dt = Application.isPlaying ? Time.deltaTime : 1f / 60f;

        // advance along path
        if (travel == TravelMode.Loop)
        {
            _s += speed * dt;
            if (_s > _pathLen) _s -= _pathLen;
        }
        else if (travel == TravelMode.PingPong)
        {
            _s += speed * dt * _dir;
            if (_s >= _pathLen) { _s = _pathLen; _dir = -1; }
            else if (_s <= 0f) { _s = 0f; _dir = 1; }
        }
        else // Once
        {
            _s = Mathf.Min(_pathLen, _s + speed * dt);
        }

        // crest center this frame
        Vector3 centerWorld = EvaluatePathAt(_s);
        Vector3 centerLocal = transform.worldToLocalMatrix.MultiplyPoint3x4(centerWorld);
        _crestLocal = centerLocal;
        _crestWorld = centerWorld;

        // gaussian deformation on local XZ
        float sigma = Mathf.Max(0.001f, radius * sharpness);
        float twoSigma2 = 2f * sigma * sigma;
        float r2limit = radius * radius * 4f;

        for (int i = 0; i < _base.Length; i++)
        {
            var v = _base[i];
            float dx = v.x - centerLocal.x;
            float dz = v.z - centerLocal.z;
            float d2 = dx * dx + dz * dz;

            float yOff = 0f;
            if (d2 < r2limit)
                yOff = height * Mathf.Exp(-d2 / twoSigma2);

            v.y = _base[i].y + yOff;
            _deformed[i] = v;
        }

        _mesh.vertices = _deformed;
        if (recalcNormals) _mesh.RecalculateNormals();
        _mesh.RecalculateBounds();

#if UNITY_WEBGL
        Debug.Log($"SIGMA:{sigma}  radius:{radius} sharpness:{sharpness}");
#endif

    }

    // ------- path helpers -------
    void RebuildPathCache()
    {
        _wpWorld.Clear(); _wpS.Clear(); _pathLen = 0f;

        if (waypoints == null || waypoints.Count < 2) return;

        for (int i = 0; i < waypoints.Count; i++)
            if (waypoints[i]) _wpWorld.Add(waypoints[i].position);

        if (_wpWorld.Count < 2) return;

        _wpS.Add(0f);
        for (int i = 1; i < _wpWorld.Count; i++)
        {
            _pathLen += Vector3.Distance(_wpWorld[i - 1], _wpWorld[i]);
            _wpS.Add(_pathLen);
        }
    }

    Vector3 EvaluatePathAt(float s)
    {
        if (_wpWorld.Count == 0) return transform.position;
        if (s <= 0f) return _wpWorld[0];
        if (s >= _pathLen) return _wpWorld[^1];

        int seg = 0;
        while (seg < _wpS.Count - 1 && _wpS[seg + 1] < s) seg++;

        float t = Mathf.InverseLerp(_wpS[seg], _wpS[seg + 1], s);
        return Vector3.Lerp(_wpWorld[seg], _wpWorld[seg + 1], t);
    }

    void Awake()
    {
        _mf = GetComponent<MeshFilter>();
        var src = originalPlaneMesh ? originalPlaneMesh : _mf.sharedMesh;
        if (src) _mf.mesh = Instantiate(src);  // fresh, readable copy
    }


    // -------------------------
    // Public helpers for boats (add to MoveBulge):
    // -------------------------

    /// Current crest center in WORLD space (along your waypoint path at _s).
    public Vector3 GetCrestWorldPos()
    {
        return EvaluatePathAt(_s);
    }

    /// Water surface height (WORLD Y) at a world XZ point for the current frame,
    /// using the same Gaussian you already use to deform the plane.
    public float GetActualMeshHeightAtWorldXZ(Vector3 worldPos)
    {
        if (_mesh == null || _deformed == null)
            return transform.position.y;

        // Convert world → local
        Vector3 local = transform.InverseTransformPoint(worldPos);

        // Find closest vertex
        float best = float.MaxValue;
        float height = 0f;

        for (int i = 0; i < _deformed.Length; i++)
        {
            float dx = _deformed[i].x - local.x;
            float dz = _deformed[i].z - local.z;
            float dist = dx * dx + dz * dz;

            if (dist < best)
            {
                best = dist;
                height = _deformed[i].y;
            }
        }

        // Convert local → world height
        Vector3 worldH = transform.TransformPoint(new Vector3(0f, height, 0f));
        return worldH.y;
    }


    /// Water height at world XZ, wrapper for easier boat code.
    public float GetWaterHeightAtWorldXZ(float x, float z)
    {
        Vector3 wp = new Vector3(x, 0f, z);
        return GetActualMeshHeightAtWorldXZ(wp);
    }

}
