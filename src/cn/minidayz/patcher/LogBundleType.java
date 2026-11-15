package cn.minidayz.patcher;
import java.io.*;import java.util.zip.*;import org.json.*;
/** Recognize this installer's own report only by its structured format marker. */
public final class LogBundleType {
 public static boolean isInstallerDiagnostic(byte[] bytes)throws Exception{
  if(bytes.length<4||bytes[0]!='P'||bytes[1]!='K')return false;
  ZipInputStream zip=new ZipInputStream(new ByteArrayInputStream(bytes));
  try{ZipEntry e;int count=0,total=0;boolean installer=false;byte[] b=new byte[8192];
   while((e=zip.getNextEntry())!=null){
    FilesEx.require(++count<=200,"E_LOG_ZIP_LIMIT");
    boolean report=!e.isDirectory()&&e.getName().equals("report.json");
    ByteArrayOutputStream out=report?new ByteArrayOutputStream():null;int item=0,n;
    // getNextEntry() silently drains the preceding entry. Drain every item here,
    // including directories and ignored binary files, under explicit bounds.
    while((n=zip.read(b))!=-1){
     item+=n;total+=n;
     FilesEx.require(item<=4194304&&total<=8388608,"E_LOG_LIMIT: 诊断包解压内容过大，请只保留日志");
     if(report){FilesEx.require(item<=196608,"E_LOG_LIMIT: report.json 超过192KB");out.write(b,0,n);}
    }
    if(report){try{JSONObject json=new JSONObject(new String(out.toByteArray(),"UTF-8"));
      installer|="mdz-diagnostic/1".equals(json.optString("format"))&&json.has("installer_version")&&json.has("engine");
     }catch(JSONException invalid){/* Classification unknown: ordinary log handling decides. */}}
    zip.closeEntry();
   }
   return installer;
  }finally{zip.close();}
 }
}
