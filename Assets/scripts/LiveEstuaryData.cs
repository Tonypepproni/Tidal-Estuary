using UnityEngine;
using UnityEngine.Networking;
using TMPro;
using System.Collections;
using SimpleJSON;

public class LiveEstuaryData : MonoBehaviour
{
    [Header("UI Text Elements")]
    public TextMeshProUGUI usgsText;
    public TextMeshProUGUI noaaText;
    public TextMeshProUGUI turkeyText;

    // ---------------------------------------------------------
    // USGS HUDSON (01376520) - Freshwater site
    // ---------------------------------------------------------
    private string usgsUrl =
        "https://waterservices.usgs.gov/nwis/iv/?format=json&sites=01376520&period=P1D";

    // ---------------------------------------------------------
    // NOAA BATTERY (8454000) - Observed water level ONLY
    // ---------------------------------------------------------
    private string batteryWaterLevel =
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" +
        "product=water_level&station=8454000&datum=MLLW&units=english&" +
        "time_zone=lst_ldt&format=json&range=6";

    // ---------------------------------------------------------
    // NOAA TURKEY POINT (8518962) - Tides + estuary chemistry
    // ---------------------------------------------------------
    private string tpPredictions =
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" +
        "product=predictions&station=8518962&interval=h&units=english&" +
        "time_zone=lst_ldt&format=json&range=24";

    private string tpHiLo =
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" +
        "product=predictions&station=8518962&interval=hilo&units=english&" +
        "time_zone=lst_ldt&format=json";

    private string tpWaterTemp =
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" +
        "product=water_temperature&station=8518962&units=metric&time_zone=lst_ldt&format=json&range=6";

    private string tpConductivity =
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" +
        "product=conductivity&station=8518962&units=metric&time_zone=lst_ldt&format=json&range=6";

    private string tpSalinity =
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" +
        "product=salinity&station=8518962&units=metric&time_zone=lst_ldt&format=json&range=6";


    void Start()
    {
        StartCoroutine(DataLoop());
    }

    IEnumerator DataLoop()
    {
        while (true)
        {
            yield return FetchAndDisplayData();
            yield return new WaitForSeconds(120f);
        }
    }

    IEnumerator FetchAndDisplayData()
    {
        // responses
        string usgsData = null;
        string wlBattery = null;

        string tpPred = null;
        string tpHL = null;
        string tpTemp = null;
        string tpCond = null;
        string tpSal = null;

        // freshwater (USGS)
        yield return StartCoroutine(Get(usgsUrl, res => usgsData = res));

        // battery water level
        yield return StartCoroutine(Get(batteryWaterLevel, res => wlBattery = res));

        // turkey point data
        yield return StartCoroutine(Get(tpPredictions, res => tpPred = res));
        yield return StartCoroutine(Get(tpHiLo, res => tpHL = res));
        yield return StartCoroutine(Get(tpWaterTemp, res => tpTemp = res));
        yield return StartCoroutine(Get(tpConductivity, res => tpCond = res));
        yield return StartCoroutine(Get(tpSalinity, res => tpSal = res));

        // update UI
        usgsText.text = BuildUSGSText(usgsData);
        noaaText.text = BuildNOAAText(wlBattery, tpPred, tpHL);
        turkeyText.text = BuildTurkeyPointText(tpTemp, tpCond, tpSal);
    }

    IEnumerator Get(string url, System.Action<string> callback)
    {
        UnityWebRequest www = UnityWebRequest.Get(url);
        yield return www.SendWebRequest();
        callback(www.result == UnityWebRequest.Result.Success ? www.downloadHandler.text : "ERROR");
    }

    // Helper formatter
    string F(float v, string fmt = "0.0")
    {
        return float.IsNaN(v) ? "N/A" : v.ToString(fmt);
    }

    // ---------------------------------------------------------
    // USGS: Freshwater Chemistry
    // ---------------------------------------------------------
    string BuildUSGSText(string raw)
    {
        JSONNode j = SafeParse(raw);

        float waterTemp = ExtractUSGS(j, "00010");
        float dissolvedO2 = ExtractUSGS(j, "00300");
        float conductivity = ExtractUSGS(j, "00095");
        float turbidity = ExtractUSGS(j, "63680");

        return
            "<b><size=38><color=#4AA3FF>USGS Freshwater</color></size></b>\n<size=30>\n" +
            $"<b>Water Temp:</b> {F(waterTemp)} °C\n" +
            $"<b>Dissolved O2:</b> {F(dissolvedO2)} mg/L\n" +
            $"<b>Conductivity:</b> {F(conductivity, "0")} µS/cm\n" +
            $"<b>Turbidity:</b> {F(turbidity)} NTU\n</size>";
    }

    // ---------------------------------------------------------
    // NOAA: Water Level (Battery) + Tides (Turkey Point)
    // ---------------------------------------------------------
    string BuildNOAAText(string batteryWL, string predictions, string hilo)
    {
        float wl = ExtractCOOPS(batteryWL);
        float predicted = ExtractPrediction(predictions);
        string hiloList = ExtractHiLo(hilo);

        return
            "<b><size=38><color=#00D9A5>NOAA Tide Data</color></size></b>\n<size=30>\n" +
            $"<b>Observed WL (Battery):</b> {F(wl, "0.00")} ft\n" +
            $"<b>Predicted Tide:</b> {F(predicted, "0.00")} ft\n\n" +
            "<b>Upcoming Tides:</b>\n" +
            (hiloList ?? "N/A") +
            "</size>";
    }

    // ---------------------------------------------------------
    // Turkey Point Chemistry (water temp, salinity, cond)
    // ---------------------------------------------------------
    string BuildTurkeyPointText(string temp, string cond, string sal)
    {
        float t = ExtractCOOPS(temp);        // °C
        float c = ExtractCOOPS(cond);        // mS/cm
        float s = ExtractCOOPS(sal);         // PSU

        return
            "<b><size=38><color=#F7C642>Turkey Point Estuary</color></size></b>\n<size=30>\n" +
            $"<b>Water Temp:</b> {F(t)} °C\n" +
            $"<b>Conductivity:</b> {F(c)} mS/cm\n" +
            $"<b>Salinity:</b> {F(s)} PSU\n" +
            "</size>";
    }

    // ---------------------------------------------------------
    // JSON SAFE PARSE
    // ---------------------------------------------------------
    JSONNode SafeParse(string raw)
    {
        try { return JSON.Parse(raw); }
        catch { return null; }
    }

    // ---------------------------------------------------------
    // EXTRACTORS
    // ---------------------------------------------------------

    float ExtractUSGS(JSONNode json, string code)
    {
        if (json == null) return float.NaN;

        foreach (JSONNode ts in json["value"]["timeSeries"])
        {
            if (ts["variable"]["variableCode"][0]["value"] == code)
            {
                string val = ts["values"][0]["value"][0]["value"];
                float.TryParse(val, out float f);
                return f;
            }
        }
        return float.NaN;
    }

    float ExtractCOOPS(string raw)
    {
        JSONNode json = SafeParse(raw);
        if (json == null || json["data"] == null || json["data"].Count == 0)
            return float.NaN;

        string val = json["data"][json["data"].Count - 1]["v"];
        float.TryParse(val, out float f);
        return f;
    }

    float ExtractPrediction(string raw)
    {
        JSONNode json = SafeParse(raw);
        if (json == null || json["predictions"] == null) return float.NaN;

        var arr = json["predictions"];
        if (arr.Count == 0) return float.NaN;

        float.TryParse(arr[arr.Count - 1]["v"], out float f);
        return f;
    }

    string ExtractHiLo(string raw)
    {
        JSONNode json = SafeParse(raw);
        if (json == null || json["predictions"] == null) return null;

        string result = "";
        foreach (JSONNode p in json["predictions"])
            result += $"{p["t"]}: {p["type"]} {p["v"]} ft\n";

        return result;
    }
}
