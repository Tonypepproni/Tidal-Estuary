using System.Collections.Generic;
using UnityEngine;

/// Boat moves EXACTLY along the given waypoints (polyline), at constant speed.
/// No bank avoidance, no physics steering. Think train-on-rails.
///
/// How to use:
/// 1) Put all your river waypoints (Transforms) in order into `waypoints`,
///    OR enable `autoCollectFromParent` and assign `waypointParent`.
/// 2) Put this script on your Boat object. Give it a Rigidbody (isKinematic=true).
/// 3) (Optional) Assign `water` to lock Y to the water surface + offset.
[RequireComponent(typeof(Rigidbody))]
public class BoatFollowWaypointsExact : MonoBehaviour
{
    [Header("Waypoints (in order)")]
    public List<Transform> waypoints = new List<Transform>();

    [Tooltip("If true, the list will be rebuilt from children of `waypointParent` in Hierarchy order.")]
    public bool autoCollectFromParent = false;
    public Transform waypointParent;

    [Header("Motion")]
    public float speed = 8f;          // meters / second along the path
    public bool loop = true;          // loop when reaching the end
    public bool orientToPath = true;  // rotate to face the path direction
    [Range(0f, 1f)] public float turnLerp = 0.2f; // 0..1 rotation smoothing per frame

    [Header("Height Lock (optional)")]
    public Transform water;           // assign your water plane/object if you want fixed Y
    public float waterYOffset = 0.2f; // raise the hull a bit

    // ---- internals ----
    Rigidbody _rb;
    readonly List<Vector3> _P = new();    // sampled world points (straight from waypoints)
    readonly List<float> _S = new();     // cumulative distance (arc-length)
    float _totalLen;
    float _s;                              // current distance along path

    void Awake()
    {
        _rb = GetComponent<Rigidbody>();
        _rb.isKinematic = false;  // we drive position ourselves
        _rb.constraints = RigidbodyConstraints.FreezeRotationX | RigidbodyConstraints.FreezeRotationZ;

        RebuildPath();
    }

    void OnValidate() { if (Application.isPlaying) RebuildPath(); }

    void RebuildPath()
    {
        _P.Clear(); _S.Clear(); _totalLen = 0f; _s = 0f;

        if (autoCollectFromParent && waypointParent)
        {
            waypoints.Clear();
            for (int i = 0; i < waypointParent.childCount; i++)
                waypoints.Add(waypointParent.GetChild(i));
        }

        foreach (var t in waypoints) if (t) _P.Add(t.position);

        if (_P.Count < 2) return;

        _S.Add(0f);
        for (int i = 1; i < _P.Count; i++)
        {
            _totalLen += Vector3.Distance(_P[i - 1], _P[i]);
            _S.Add(_totalLen);
        }
    }

    void Update()
    {
        if (_P.Count < 2 || _totalLen <= 0f) return;

        // advance along arc-length
        _s += speed * Time.deltaTime;
        if (loop) _s = Mathf.Repeat(_s, _totalLen);
        else _s = Mathf.Min(_s, _totalLen - 0.0001f);

        // sample position & forward on the polyline
        Vector3 pos, fwd;
        EvaluateAt(_s, out pos, out fwd);

        // lock Y to water if provided
        if (water)
        {
            pos.y = water.position.y + waterYOffset;
        }

        // move
        _rb.MovePosition(pos);

        // face path direction (keep upright)
        if (orientToPath && fwd.sqrMagnitude > 0.0001f)
        {
            var look = Quaternion.LookRotation(new Vector3(fwd.x, 0f, fwd.z), Vector3.up);
            _rb.MoveRotation(Quaternion.Slerp(transform.rotation, look, turnLerp));
        }
    }

    // Sample position & direction at arc-length s along the polyline
    void EvaluateAt(float s, out Vector3 pos, out Vector3 fwd)
    {
        if (s <= 0f) { pos = _P[0]; fwd = (_P[1] - _P[0]).normalized; return; }
        if (s >= _totalLen) { pos = _P[^1]; fwd = (_P[^1] - _P[^2]).normalized; return; }

        // find segment containing s (linear scan is fine for dozens/hundreds)
        int i = 0;
        while (i < _S.Count - 1 && _S[i + 1] < s) i++;

        float t = Mathf.InverseLerp(_S[i], _S[i + 1], s);
        pos = Vector3.Lerp(_P[i], _P[i + 1], t);
        fwd = (_P[i + 1] - _P[i]).normalized;
    }

    // Optional helper to jump the boat to the start of the path
    [ContextMenu("Snap To Start")]
    void SnapToStart()
    {
        if (_P.Count >= 2)
        {
            _s = 0f;
            Vector3 pos, fwd; EvaluateAt(_s, out pos, out fwd);
            if (water) pos.y = water.position.y + waterYOffset;
            transform.position = pos;
            if (orientToPath) transform.rotation = Quaternion.LookRotation(new Vector3(fwd.x, 0f, fwd.z), Vector3.up);
        }
    }
}
