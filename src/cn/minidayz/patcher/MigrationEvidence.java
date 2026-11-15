package cn.minidayz.patcher;
import java.io.*;import java.util.zip.*;import org.json.*;
/** Component identities are evidence for migration, never permission to patch. */
public final class MigrationEvidence {
 public static JSONObject scan(File apk,FilesEx.Watch w)throws Exception{
  JSONArray components=new JSONArray(),blockers=new JSONArray();boolean metadata=false;
  ZipFile z=new ZipFile(apk);
  try{for(ZipEntry e:FilesEx.entries(z).values()){
   String n=e.getName();if(e.isDirectory())continue;
   boolean meta=n.endsWith("/global-metadata.dat");
   if(!(meta||n.equals("AndroidManifest.xml")||n.matches("classes[0-9]*\\.dex")||(n.startsWith("lib/")&&n.endsWith(".so"))||n.endsWith("/data.unity3d")))continue;
   FilesEx.check(w);InputStream input=z.getInputStream(e);String sha;
   try{sha=FilesEx.hex(FilesEx.digest(input,w));}finally{input.close();}
   JSONObject item=new JSONObject().put("entry",n).put("size",e.getSize()).put("sha256",sha);
   if(meta){metadata=true;byte[] h=new byte[8];DataInputStream in=new DataInputStream(z.getInputStream(e));
    try{in.readFully(h);}finally{in.close();}
    int magic=ProjectAnalysis.le(h,0),version=ProjectAnalysis.le(h,4);
    boolean known=magic==0xfab11baf&&(version==24||version==27||version==29||version==31||version==39);
    item.put("header_version",version).put("known_layout_version",known);
    if(!known)blockers.put("元数据布局不受当前分析流程支持："+version+"；需验证布局，禁止仅修改版本字段后复用旧地址。");
   }components.put(item);
  }}finally{z.close();}
  if(!metadata)blockers.put("未找到 IL2CPP metadata；不能建立原生方法迁移依据。");
  return new JSONObject().put("format","mdz-migration-evidence/1").put("components",components).put("blockers",blockers)
   .put("automatic_native_migration",false).put("release_ready",false)
   .put("next_step","按完整方法签名重定位，核验字段与调用ABI；仅复用已证明不变的功能，完成游戏回归后封装签名适配档案。");
 }
}
