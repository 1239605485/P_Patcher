package cn.minidayz.patcher;
import android.content.*;import android.database.*;import android.net.Uri;import java.io.*;import org.json.*;
/** Explicit SAF access only; never probes another app's private storage. */
public final class GameLogs {
 public static void importLog(Jobs j,Uri uri,String name)throws Exception{FilesEx.check(j);InputStream in=j.ctx.getContentResolver().openInputStream(uri);FilesEx.require(in!=null,"E_LOG_OPEN: 无法读取日志，请重新选择");String text;try{text=AiWorkspace.logs(in);}finally{in.close();}FilesEx.require(text.trim().length()>0,"E_LOG_EMPTY: 未发现可读取文本日志");text=AiClient.redact(text,new AiSettings(j.ctx).secret());FilesEx.check(j);File tmp=new File(j.root,"game-log.pending");FilesEx.write(tmp,text.getBytes("UTF-8"));FilesEx.atomic(tmp,new File(j.root,"game-log.txt"));JSONObject meta=new JSONObject().put("name",AiClient.redact(name,null)).put("imported_ms",System.currentTimeMillis()).put("characters",text.length()).put("status","等待分析，尚未修复");FilesEx.write(new File(j.root,"game-log-meta.json"),meta.toString(2).getBytes("UTF-8"));j.stage("game-log-loaded","游戏日志已读取并脱敏，可进入AI分析");}
 public static String text(Jobs j)throws Exception{File f=new File(j.root,"game-log.txt");return f.isFile()?new String(FilesEx.read(new FileInputStream(f),1048576),"UTF-8"):"";}
}
