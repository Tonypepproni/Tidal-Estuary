TIDAL ESTUARY — UNITY 6 PROJECT SETUP GUIDE
==========================================

Welcome to the Tidal Estuary project!
This guide explains how to set up the Unity project locally after pulling from GitHub.

--------------------------------------------------
1. UNITY VERSION
--------------------------------------------------
This project uses:

Unity 6 (6000.x.x)

All team members MUST use Unity 6 to avoid missing shaders, errors, or material issues.

--------------------------------------------------
2. REQUIRED ASSET FOLDERS (NOT INCLUDED IN GITHUB)
--------------------------------------------------
Large assets are ignored in Git to keep the repository small.

After cloning, you MUST manually add these two folders:

1)  Assets/SkySeries Freebie/
2)  Assets/YughuesFreeSandMaterials/

These will be provided through Google Drive or shared locally.

Once added, terrain textures and skyboxes will appear correctly.

--------------------------------------------------
3. WATER SETUP
--------------------------------------------------
The river uses a lightweight stylized water material from Bitgem.

Water Material Used:
Assets/Bitgem/Materials/example-water-02.mat

This material:
- Works in Unity 6
- Works in WebGL
- Works with the MoveBulge script
- Requires no extra setup

The prefab "water.prefab" already uses this material.

--------------------------------------------------
4. HOW TO RUN THE PROJECT
--------------------------------------------------

STEP 1 — Clone the repository:
git clone https://github.com/Tonypepproni/Tidal-Estuary.git

STEP 2 — Switch to your branch:
git checkout hector
(or your assigned branch)

STEP 3 — Open the project in Unity Hub:
Select the folder containing:
Assets/
Packages/
ProjectSettings/

STEP 4 — Add the missing folders:
Copy these into your cloned project:
Assets/SkySeries Freebie/
Assets/YughuesFreeSandMaterials/

Unity will automatically reimport them.

STEP 5 — Open the main scene:
Located in:
Assets/Scenes/

Everything should now display correctly.

--------------------------------------------------
5. DO NOT COMMIT THESE FOLDERS OR FILES
--------------------------------------------------
These are intentionally ignored by .gitignore:

Library/
Temp/
Obj/
Build/
Builds/
SkySeries Freebie/
YughuesFreeSandMaterials/
Terrain/
*.unitypackage
Any file over 100MB

If these show up in "git status", DO NOT add or commit them.

--------------------------------------------------
6. NOTES FOR TEAM MEMBERS
--------------------------------------------------
- Terrain looks pink? → You forgot to add the sand materials.
- Skybox missing? → Add the SkySeries folder.
- Water not visible? → Reassign material:
  Bitgem → example-water-02.mat
- Everything else is included and should work instantly.

--------------------------------------------------
You're all set!
--------------------------------------------------
Once the two folders are added, the project works perfectly in Unity 6 and WebGL.

