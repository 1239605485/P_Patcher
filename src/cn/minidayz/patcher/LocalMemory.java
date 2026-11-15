package cn.minidayz.patcher;
import java.io.*;import org.json.*;
/** Advisory history only: never replaces signed module or content verification. */
public final class LocalMemory {
 final File file;public LocalMemory(File root){file=new File(root,"success-history.json");}
 JSONObject read(){try{if(file.isFile())return new JSONObject(new String(FilesEx.read(new FileInputStream(file),1048576),"UTF-8"));}catch(Exception ignored){}return new JSONObject();}
 public synchronized JSONObject get(String apk,String module){return read().optJSONObject(apk+":"+module);}
 public synchronized void remember(PatchEngine.Plan plan,ReleaseOptions release)throws Exception{JSONObject all=read(),item=new JSONObject().put("profile_id",plan.profile.getString("id")).put("match_mode",plan.matchMode).put("release_name",release.name).put("release_version",release.version).put("release_code",release.code).put("verified_ms",System.currentTimeMillis());if(all.length()>=32&&!all.has(plan.apkSha+":"+plan.moduleSha)){String oldest=null;long time=Long.MAX_VALUE;java.util.Iterator<?> keys=all.keys();while(keys.hasNext()){String k=(String)keys.next();long t=all.getJSONObject(k).optLong("verified_ms",0);if(t<time){oldest=k;time=t;}}if(oldest!=null)all.remove(oldest);}all.put(plan.apkSha+":"+plan.moduleSha,item);File tmp=new File(file.getParentFile(),"history.pending");FilesEx.write(tmp,all.toString(2).getBytes("UTF-8"));FilesEx.atomic(tmp,file);}
}
