// Assets/Editor/SaveMeshAsset.cs
using UnityEditor;
using UnityEngine;

public static class SaveMeshAsset
{
    [MenuItem("Tools/Save Selected Mesh As Asset")]
    public static void SaveSelectedMesh()
    {
        var mf = Selection.activeGameObject?.GetComponent<MeshFilter>();
        if (!mf || !mf.sharedMesh) { Debug.LogError("Select a GameObject with a MeshFilter"); return; }

        string path = EditorUtility.SaveFilePanelInProject("Save Mesh", mf.sharedMesh.name + "_asset", "asset", "");
        if (string.IsNullOrEmpty(path)) return;

        Mesh copy = Object.Instantiate(mf.sharedMesh);
        AssetDatabase.CreateAsset(copy, path);
        AssetDatabase.SaveAssets();
        Debug.Log("Saved mesh asset to: " + path);
    }
}
