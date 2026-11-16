package cn.minidayz.patcher;
import org.json.JSONObject;
/** Four display phases; inspection alone never claims an APK was produced. */
public final class BuildSteps {
 public static int phase(JSONObject report){
  if(report.optBoolean("signature_verified")&&"success".equals(report.optString("status")))return 3;
  String s=report.optString("stage");
  if(s.equals("identity")||s.equals("sign")||s.equals("verify")||s.equals("complete"))return 2;
  if(s.startsWith("apply:")||s.startsWith("unity")||s.equals("normalize")||s.equals("release")||s.equals("repack"))return 1;
  return 0;
 }
}
