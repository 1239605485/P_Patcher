package cn.minidayz.patcher;
import java.io.*;import org.json.*;
/** User-declared association for logs without version fields; never overrides conflicting evidence. */
public final class LogAssociation {
 public static JSONObject bind(String apk,String module,String log)throws Exception{return new JSONObject().put("input_sha256",apk).put("module_sha256",module).put("log_sha256",log).put("confirmed_ms",System.currentTimeMillis());}
 public static boolean matches(JSONObject binding,String apk,String module,String log,String evidence){return "unknown".equals(evidence)&&apk.equals(binding.optString("input_sha256"))&&module.equals(binding.optString("module_sha256"))&&log.equals(binding.optString("log_sha256"));}
 public static void confirm(Jobs j)throws Exception{FilesEx.require(j.file(1).isFile()&&j.file(2).isFile(),"E_INPUT_MISSING: 请先导入APK和插件");String text=GameLogs.text(j);FilesEx.require(text.length()>0,"E_LOG_EMPTY: 请先导入P14诊断ZIP");JSONObject c=LogEvidence.compare(text,LocalAssistant.identity(j,j.file(1)));FilesEx.require(c.getString("status").equals("unknown"),"E_LOCAL_LOG_IDENTITY: 日志已有版本信息，请先运行本地诊断；不能用手动声明覆盖冲突");JSONObject b=bind(FilesEx.sha(j.file(1),j),FilesEx.sha(j.file(2),j),AiWorkspace.hash(text.getBytes("UTF-8")));File f=new File(j.root,"log-association.pending");FilesEx.write(f,b.toString().getBytes("UTF-8"));FilesEx.atomic(f,new File(j.root,"log-association.json"));j.stage("log-associated","已记录你确认的日志归属；APK、插件或日志变化后自动失效");}
}
