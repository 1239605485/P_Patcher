package cn.minidayz.patcher;
import java.io.*;import org.json.*;
/** Local replay of exact, user-tested fixes. Never matches on version name alone. */
public final class RepairRules {
 final File file;
 String logHash()throws Exception{File f=new File(file.getParentFile(),"game-log.txt");return f.isFile()?FilesEx.sha(f,FilesEx.QUIET):AiWorkspace.hash(new byte[0]);}public RepairRules(File root){file=new File(root,"repair-rules.json");}
 public JSONArray read()throws Exception{if(!file.isFile())return new JSONArray();return new JSONArray(new String(FilesEx.read(new FileInputStream(file),2097152),"UTF-8"));}
 void save(JSONArray list)throws Exception{File tmp=new File(file.getParentFile(),"repair-rules.pending");FilesEx.write(tmp,list.toString(2).getBytes("UTF-8"));FilesEx.atomic(tmp,file);}
 public void remember(JSONObject proposal,String entry,String apk,String module,String outputModule,String before,String after)throws Exception{JSONArray old=read(),a=new JSONArray();for(int i=Math.max(0,old.length()-2);i<old.length();i++)a.put(old.getJSONObject(i));a.put(new JSONObject().put("id",System.currentTimeMillis()+"-"+outputModule.substring(0,Math.min(12,outputModule.length()))).put("entry",entry).put("apk_sha256",apk).put("module_sha256",module).put("output_module_sha256",outputModule).put("before_sha256",before).put("after_sha256",after).put("proposal",proposal).put("log_sha256",proposal.optString("_log_sha256",logHash())).put("user_tested",false).put("created_ms",System.currentTimeMillis()));save(a);}
 public JSONObject eligible(String apk,String module)throws Exception{JSONArray a=read();for(int i=a.length()-1;i>=0;i--){JSONObject r=a.getJSONObject(i);if(r.optBoolean("user_tested")&&apk.equals(r.optString("apk_sha256"))&&module.equals(r.optString("module_sha256"))&&logHash().equals(r.optString("log_sha256")))return r;}return null;}
 public JSONObject latest()throws Exception{JSONArray a=read();return a.length()==0?null:a.getJSONObject(a.length()-1);}
 public void confirmLatest(String currentModule)throws Exception{JSONArray a=read();FilesEx.require(a.length()>0,"E_RULE_EMPTY: 还没有可确认的修复记录");JSONObject r=a.getJSONObject(a.length()-1);FilesEx.require(currentModule.equals(r.getString("output_module_sha256")),"E_RULE_STALE: 当前插件不是最近修复结果，不能标记为已实测");r.put("user_tested",true).put("confirmed_ms",System.currentTimeMillis());save(a);}
}
