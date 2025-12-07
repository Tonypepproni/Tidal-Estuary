using UnityEngine;
using UnityEngine.SceneManagement;
using TMPro;
using UnityEngine.EventSystems;

public class SceneButton : MonoBehaviour, IPointerClickHandler
{
    [Header("Name of Scene to Load")]
    public string sceneName;

    // Called automatically when user clicks on this UI object
    public void OnPointerClick(PointerEventData eventData)
    {
        SceneManager.LoadScene(sceneName);
    }
}
