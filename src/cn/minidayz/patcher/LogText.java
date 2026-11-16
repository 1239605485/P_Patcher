package cn.minidayz.patcher;
import java.io.*;import java.util.*;import java.util.zip.*;import java.nio.*;import java.nio.charset.*;
/** Bounded local text import and credential redaction, without network access. */
public final class LogText {
 private static String decode(byte[] b)throws Exception{
  try{return Charset.forName("UTF-8").newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(b)).toString();}
  catch(CharacterCodingException e){throw new IOException("E_LOG_ENCODING: 日志须为 UTF-8 文本");}
 }
 public static String read(byte[] data)throws Exception{
  if(data.length<4||data[0]!='P'||data[1]!='K')return decode(data);
  StringBuilder text=new StringBuilder();ZipInputStream zip=new ZipInputStream(new ByteArrayInputStream(data));
  try{ZipEntry e;int count=0,total=0;byte[] b=new byte[8192];
   while((e=zip.getNextEntry())!=null){FilesEx.require(++count<=200,"E_LOG_ZIP_LIMIT");
    String name=e.getName().toLowerCase(Locale.US);
    boolean take=!e.isDirectory()&&(name.endsWith(".txt")||name.endsWith(".log")||name.endsWith(".json"))&&!name.contains("secret")&&!name.contains("key");
    ByteArrayOutputStream out=take?new ByteArrayOutputStream():null;int item=0,n;
    while((n=zip.read(b))!=-1){item+=n;total+=n;FilesEx.require(item<=4194304&&total<=8388608,"E_LOG_LIMIT: 解压日志超过限制");if(take)out.write(b,0,n);}
    if(take)text.append("\n--- ").append(e.getName()).append(" ---\n").append(decode(out.toByteArray()));
    zip.closeEntry();
   }
  }finally{zip.close();}return text.toString();
 }
 public static String redact(String text){
  if(text==null)return "";
  return text.replaceAll("(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----","[私钥已隐藏]")
   .replaceAll("(?i)(Bearer\\s+)[A-Za-z0-9._~+/=-]+","$1[已隐藏]")
   .replaceAll("(?i)((?:api[_-]?key|access[_-]?token|password|authorization)[\\\"']?\\s*[:=]\\s*[\\\"']?)[^\\s\\\"',}]+","$1[已隐藏]")
   .replaceAll("sk-[A-Za-z0-9_-]{12,}","[密钥已隐藏]");
 }
}
