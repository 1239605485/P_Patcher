package cn.minidayz.patcher;
import android.content.SharedPreferences;
/** Retain the old output but do not claim it came from newly selected inputs. */
public final class OutputProvenance {
 public static int state(SharedPreferences p){
  if(!p.getBoolean("output_provenance_known",false)||!p.getBoolean("output_release_settings_known",false))return 0;
  if(p.getBoolean("previous_output_stale",true))return 1;
  for(String field:new String[]{"name","version","code"})
   if(!p.getString("release_"+field,"").trim().equals(p.getString("output_requested_"+field,"").trim()))return 1;
  return 2;
 }
 public static boolean importMakesStale(boolean hasOutput,int kind,boolean known,String expected,String imported){
  return hasOutput&&(kind==1||kind==2||kind==4)&&(!known||expected==null||expected.length()==0||!expected.equals(imported));
 }
 public static void imported(SharedPreferences prefs,int kind,String sha,boolean hasOutput){
  if(kind!=1&&kind!=2&&kind!=4)return;
  String expected=prefs.getString(kind==1?"output_input_sha256":kind==4?"output_engine_sha256":"output_module_sha256","");
  if(importMakesStale(hasOutput,kind,prefs.getBoolean("output_provenance_known",false),expected,sha))
   prefs.edit().putBoolean("output_provenance_known",true).putBoolean("previous_output_stale",true).commit();
 }
}
