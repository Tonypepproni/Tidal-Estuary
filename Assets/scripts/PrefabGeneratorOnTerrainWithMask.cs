using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Spawns prefabs on a Terrain, avoiding a river area defined by a mask texture
/// (white = river, black = land). The mask is mapped to a world-space rectangle.
/// Each spawned prefab is snapped so its *visible bottom* touches the terrain.
/// </summary>
[RequireComponent(typeof(Terrain))]
public class PrefabGeneratorOnTerrainWithMask : MonoBehaviour
{
    [Header("Terrain & Area")]
    public Terrain terrain;                     // auto-filled on Awake if null
    [Tooltip("Keep spawns this far from terrain edges (meters).")]
    public float edgeMargin = 2f;

    [Header("River Mask (white = river, black = land)")]
    public Texture2D riverMask;                 // must be Read/Write Enabled
    [Tooltip("World-space rect that the mask covers. X/Z min,max in meters.")]
    public Vector2 worldMinXZ;                  // default = terrain bottom-left (x,z)
    public Vector2 worldMaxXZ;                  // default = terrain top-right  (x,z)
    [Range(0f, 1f)]
    public float riverThreshold = 0.5f;         // > threshold counts as river
    [Tooltip("Extra no-spawn padding around river (meters).")]
    public float inflateRiverMeters = 5f;

    [Header("What & How Many")]
    public List<GameObject> prefabs;
    public int count = 200;

    [Header("Transform")]
    [Tooltip("Random uniform scale [min,max]")]
    public Vector2 scaleRange = new Vector2(0.8f, 1.6f);
    [Tooltip("Align spawned objects to terrain normal.")]
    public bool alignToSlope = true;
    [Tooltip("Extra height offset after snapping (positive lifts, negative sinks).")]
    public float yOffset = 0f;
    public Transform parent;

    [Header("Placement filters (optional)")]
    [Tooltip("Max slope (degrees) to allow spawning. Set high (e.g., 90) to ignore.")]
    [Range(0f, 90f)] public float maxSlope = 40f;

    [Tooltip("Max attempts per spawn to find a valid land position.")]
    public int maxTriesPerSpawn = 25;

    [Header("Snapping options")]
    [Tooltip("Push slightly into the ground to avoid hovering due to smoothing.")]
    public float extraSink = 0.02f;
    [Tooltip("Use a downward raycast to find the exact collider hit (good if you have additional colliders). "
           + "If false, uses Terrain.SampleHeight.")]
    public bool snapUsingRaycast = true;

    // cached
    TerrainData _td;
    Vector3 _tPos;
    float _maskUPerMeter, _maskVPerMeter;   // pixels per meter in X/Z

    void Awake()
    {
        if (!terrain) terrain = GetComponent<Terrain>();
        _td = terrain.terrainData;
        _tPos = terrain.GetPosition();

        // Default mask rect = whole terrain if not set
        if (Mathf.Approximately(worldMaxXZ.x, 0f) && Mathf.Approximately(worldMaxXZ.y, 0f))
        {
            worldMinXZ = new Vector2(_tPos.x, _tPos.z);
            worldMaxXZ = new Vector2(_tPos.x + _td.size.x, _tPos.z + _td.size.z);
        }

        if (riverMask)
        {
            float worldWidth = Mathf.Max(0.001f, worldMaxXZ.x - worldMinXZ.x);
            float worldHeight = Mathf.Max(0.001f, worldMaxXZ.y - worldMinXZ.y);
            _maskUPerMeter = riverMask.width / worldWidth;
            _maskVPerMeter = riverMask.height / worldHeight;
        }
    }

    void OnValidate()
    {
        if (scaleRange.y < scaleRange.x) scaleRange.y = scaleRange.x;
        if (maxTriesPerSpawn < 1) maxTriesPerSpawn = 1;
        extraSink = Mathf.Max(0f, extraSink);
    }

    void Start()
    {
        if (prefabs == null || prefabs.Count == 0 || terrain == null) return;
        if (!riverMask)
        {
            Debug.LogWarning("[PrefabGeneratorOnTerrainWithMask] No riverMask assigned. Spawning everywhere.");
        }
        else if (!riverMask.isReadable)
        {
            Debug.LogError("[PrefabGeneratorOnTerrainWithMask] Mask not readable. Enable Read/Write in Texture Import Settings.");
            return;
        }

        SpawnAll();
    }

    void SpawnAll()
    {
        var size = _td.size;
        float minX = _tPos.x + edgeMargin;
        float maxX = _tPos.x + size.x - edgeMargin;
        float minZ = _tPos.z + edgeMargin;
        float maxZ = _tPos.z + size.z - edgeMargin;

        for (int i = 0; i < count; i++)
        {
            bool placed = false;
            for (int tries = 0; tries < maxTriesPerSpawn; tries++)
            {
                float x = Random.Range(minX, maxX);
                float z = Random.Range(minZ, maxZ);

                // Skip if river mask says "river"
                if (IsInRiver(x, z)) continue;

                // Sample terrain height and normal for filtering/rotation
                float ySample = terrain.SampleHeight(new Vector3(x, 0f, z)) + _tPos.y;
                Vector3 normal = _td.GetInterpolatedNormal(
                    Mathf.InverseLerp(_tPos.x, _tPos.x + size.x, x),
                    Mathf.InverseLerp(_tPos.z, _tPos.z + size.z, z)
                );

                // Slope filter
                if (maxSlope < 90f)
                {
                    float slopeDeg = Vector3.Angle(normal, Vector3.up);
                    if (slopeDeg > maxSlope) continue;
                }

                // Pick prefab, rotation & scale
                int which = Random.Range(0, prefabs.Count);
                float s = Random.Range(scaleRange.x, scaleRange.y);

                Quaternion rot = alignToSlope
                    ? Quaternion.FromToRotation(Vector3.up, normal)
                    : Quaternion.identity;

                // Start roughly at sampled height; we’ll bottom-snap next
                Vector3 pos = new Vector3(x, ySample, z);
                var go = Instantiate(prefabs[which], pos, rot, parent);
                go.transform.localScale = Vector3.one * s;

                // **Bottom snap to terrain** (handles middle pivots & odd meshes)
                SnapToTerrainBottom(go, extraSink + yOffset);

                placed = true;
                break;
            }
            // if (!placed) Debug.LogWarning("Failed to place an item after max tries.");
        }
    }

    /// <summary>
    /// Moves the object vertically so the *lowest rendered point* sits on the terrain.
    /// Adds a small extraSink (positive value sinks slightly) and user yOffset.
    /// </summary>
    void SnapToTerrainBottom(GameObject go, float sinkPlusOffset)
    {
        // 1) Find precise ground Y under the object’s XZ using raycast or sample
        Vector3 p = go.transform.position;
        float groundY;

        if (snapUsingRaycast)
        {
            // Shoot from well above down to catch terrain collider (and any other colliders)
            float up = 1000f;
            Vector3 origin = new Vector3(p.x, p.y + up, p.z);
            if (Physics.Raycast(origin, Vector3.down, out RaycastHit hit, up * 2f))
                groundY = hit.point.y;
            else
                groundY = terrain.SampleHeight(p) + _tPos.y;
        }
        else
        {
            groundY = terrain.SampleHeight(p) + _tPos.y;
        }

        // 2) Compute rendered bottom (bounds.min.y) in world space
        Renderer[] rends = go.GetComponentsInChildren<Renderer>();
        if (rends == null || rends.Length == 0)
        {
            // No renderer, just fall back to sampled height
            go.transform.position = new Vector3(p.x, groundY + sinkPlusOffset, p.z);
            return;
        }

        Bounds b = rends[0].bounds;
        for (int i = 1; i < rends.Length; i++) b.Encapsulate(rends[i].bounds);
        float bottom = b.min.y;

        // 3) Raise/lower so bottom sits at groundY, with tiny sink to avoid hover
        float deltaY = (groundY - bottom) + sinkPlusOffset;
        go.transform.position += new Vector3(0f, deltaY, 0f);
    }

    bool IsInRiver(float wx, float wz)
    {
        if (!riverMask) return false;

        // Convert world xz to mask UV
        float u = Mathf.InverseLerp(worldMinXZ.x, worldMaxXZ.x, wx);
        float v = Mathf.InverseLerp(worldMinXZ.y, worldMaxXZ.y, wz);

        if (u < 0f || u > 1f || v < 0f || v > 1f) return false; // outside mask rect

        int px = Mathf.Clamp(Mathf.RoundToInt(u * (riverMask.width - 1)), 0, riverMask.width - 1);
        int py = Mathf.Clamp(Mathf.RoundToInt(v * (riverMask.height - 1)), 0, riverMask.height - 1);

        // Inflate river band by N meters using a small pixel radius
        int inflatePx = Mathf.CeilToInt(inflateRiverMeters * 0.5f * (_maskUPerMeter + _maskVPerMeter)); // avg px/meter
        int r = Mathf.Max(0, inflatePx);

        for (int dy = -r; dy <= r; dy++)
        {
            int sy = Mathf.Clamp(py + dy, 0, riverMask.height - 1);
            for (int dx = -r; dx <= r; dx++)
            {
                int sx = Mathf.Clamp(px + dx, 0, riverMask.width - 1);
                Color c = riverMask.GetPixel(sx, sy);
                float vLuma = c.grayscale; // 0..1
                if (vLuma >= riverThreshold) return true; // inside river band
            }
        }
        return false;
    }

#if UNITY_EDITOR
    void OnDrawGizmosSelected()
    {
        if (!terrain) terrain = GetComponent<Terrain>();
        if (!terrain) return;

        var size = terrain.terrainData.size;
        var pos  = terrain.GetPosition();
        Gizmos.color = new Color(0f, 1f, 1f, 0.15f);
        Gizmos.DrawCube(new Vector3(pos.x + size.x * 0.5f, pos.y + 0.1f, pos.z + size.z * 0.5f),
                        new Vector3(size.x - edgeMargin * 2f, 0.2f, size.z - edgeMargin * 2f));

        // Draw mask rect in yellow
        Gizmos.color = new Color(1f, 1f, 0f, 0.35f);
        float cx = (worldMinXZ.x + worldMaxXZ.x) * 0.5f;
        float cz = (worldMinXZ.y + worldMaxXZ.y) * 0.5f;
        float sx = Mathf.Abs(worldMaxXZ.x - worldMinXZ.x);
        float sz = Mathf.Abs(worldMaxXZ.y - worldMinXZ.y);
        Gizmos.DrawWireCube(new Vector3(cx, pos.y + 0.2f, cz), new Vector3(sx, 0.05f, sz));
    }
#endif
}
