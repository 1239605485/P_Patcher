package cn.minidayz.patcher;
import android.content.*;import android.database.*;import android.net.Uri;import java.io.*;import org.json.*;
/** Explicit SAF access only; never probes another app's private storage. */
public final class GameLogs {
 public static void importLog(Jobs j,Uri uri,String name)throws Exception{FilesEx.check(j);InputStream in=j.ctx.getContentResolver().openInputStream(uri);FilesEx.require(in!=null,"E_LOG_OPEN: 无法读取日志，请重新选择");byte[] data=FilesEx.read(in,4194304);FilesEx.require(!LogBundleType.isInstallerDiagnostic(data),"E_LOG_INSTALLER_DIAGNOSTIC: 此文件是补丁助手诊断，不是游戏运行日志");String text=LogText.read(data);FilesEx.require(text.trim().length()>0,"E_LOG_EMPTY: 未发现可读取文本日志");text=LogText.redact(text);FilesEx.check(j);File tmp=new File(j.root,"game-log.pending");FilesEx.write(tmp,text.getBytes("UTF-8"));FilesEx.atomic(tmp,new File(j.root,"game-log.txt"));JSONObject meta=new JSONObject().put("name",LogText.redact(name)).put("imported_ms",System.currentTimeMillis()).put("characters",text.length()).put("status","仅保存，供排查参考");FilesEx.write(new File(j.root,"game-log-meta.json"),meta.toString(2).getBytes("UTF-8"));j.stage("game-log-loaded","游戏日志已保存并脱敏，可随安装器诊断导出");}
 public static String text(Jobs j)throws Exception{File f=new File(j.root,"game-log.txt");return f.isFile()?new String(FilesEx.read(new FileInputStream(f),16777216),"UTF-8"):"";}
}
