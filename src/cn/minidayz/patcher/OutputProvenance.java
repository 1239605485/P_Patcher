package cn.minidayz.patcher;
import android.content.SharedPreferences;
/** Retain the old output but do not claim it came from newly selected inputs. */
public final class OutputProvenance {
 public static boolean importMakesStale(boolean hasOutput,int kind,boolean known,String expected,String imported){
  return hasOutput&&(kind==1||kind==2)&&(!known||expected==null||expected.length()==0||!expected.equals(imported));
 }
 public static void imported(SharedPreferences prefs,int kind,String sha,boolean hasOutput){
  if(kind!=1&&kind!=2)return;
  String expected=prefs.getString(kind==1?"output_input_sha256":"output_module_sha256","");
  if(importMakesStale(hasOutput,kind,prefs.getBoolean("output_provenance_known",false),expected,sha))
   prefs.edit().putBoolean("output_provenance_known",true).putBoolean("previous_output_stale",true).commit();
 }
}
