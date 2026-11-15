package cn.minidayz.patcher;
import java.io.*;import java.security.*;import java.util.*;import java.util.zip.*;
public final class FilesEx {
 public interface Watch {void stage(String stage,String message);void progress(long done,long total);boolean cancelled();}
 public static final Watch QUIET=new Watch(){public void stage(String s,String m){}public void progress(long d,long t){}public boolean cancelled(){return false;}};
 public static void check(Watch w)throws IOException{if(w.cancelled())throw new IOException("E_CANCELLED: 已取消，上一份结果保留");}
 public static void require(boolean value,String msg)throws IOException{if(!value)throw new IOException(msg);}
 public static byte[] read(InputStream in,int max)throws IOException{try{ByteArrayOutputStream b=new ByteArrayOutputStream();byte[] a=new byte[65536];int n;while((n=in.read(a))!=-1){if(b.size()+n>max)throw new IOException("E_LIMIT: 文件超过允许大小");b.write(a,0,n);}return b.toByteArray();}finally{in.close();}}
 public static void copy(InputStream in,OutputStream out,Watch w)throws IOException{byte[] a=new byte[131072];int n;while((n=in.read(a))!=-1){check(w);out.write(a,0,n);}}
 public static void slice(RandomAccessFile in,OutputStream out,long count,Watch w)throws IOException{byte[] b=new byte[131072];while(count>0){check(w);int n=in.read(b,0,(int)Math.min(b.length,count));if(n<0)throw new EOFException("E_DELTA_EOF");out.write(b,0,n);count-=n;}}
 public static String hex(byte[] b){StringBuilder s=new StringBuilder();for(byte v:b)s.append(String.format(Locale.US,"%02x",v&255));return s.toString();}
 public static byte[] digest(InputStream in,Watch w)throws Exception{try{MessageDigest d=MessageDigest.getInstance("SHA-256");byte[] b=new byte[131072];int n;while((n=in.read(b))!=-1){check(w);d.update(b,0,n);}return d.digest();}finally{in.close();}}
 public static String sha(File f,Watch w)throws Exception{InputStream in=new FileInputStream(f);try{MessageDigest d=MessageDigest.getInstance("SHA-256");byte[] b=new byte[131072];int n;long done=0;w.progress(0,f.length());while((n=in.read(b))!=-1){check(w);d.update(b,0,n);done+=n;w.progress(done,f.length());}return hex(d.digest());}finally{in.close();}}
 public static void write(File f,byte[] b)throws IOException{FileOutputStream out=new FileOutputStream(f);try{out.write(b);out.getFD().sync();}finally{out.close();}}
 public static void atomic(File temp,File dest)throws IOException{if(!temp.renameTo(dest))throw new IOException("E_RENAME: 无法提交文件");}
 public static void deleteTree(File f){File[] a=f.listFiles();if(a!=null)for(File x:a)deleteTree(x);f.delete();}
 public static boolean safeName(String n){if(n.length()==0||n.startsWith("/")||n.indexOf('\\')>=0||n.indexOf('\u0000')>=0)return false;for(String s:n.split("/"))if(s.equals("..")||s.equals("."))return false;return true;}
 public static boolean signature(String n){String s=n.toUpperCase(Locale.US);return s.startsWith("META-INF/")&&(s.endsWith(".SF")||s.endsWith(".RSA")||s.endsWith(".DSA")||s.endsWith(".EC")||s.endsWith("MANIFEST.MF"));}
 public static Map<String,ZipEntry> entries(ZipFile z)throws IOException{Map<String,ZipEntry> map=new LinkedHashMap<String,ZipEntry>();Enumeration<? extends ZipEntry> e=z.entries();while(e.hasMoreElements()){ZipEntry x=e.nextElement();require(safeName(x.getName()),"E_ZIP_PATH: 非法归档路径");require(!map.containsKey(x.getName()),"E_ZIP_DUPLICATE: 重复归档项");require(map.size()<40000,"E_ZIP_LIMIT: 归档项过多");require(x.getSize()>=0&&x.getSize()<2147483648L,"E_ZIP_LIMIT: 归档项过大");map.put(x.getName(),x);}return map;}
 public static long crc(File f)throws IOException{CRC32 c=new CRC32();InputStream in=new FileInputStream(f);try{byte[] b=new byte[131072];int n;while((n=in.read(b))!=-1)c.update(b,0,n);}finally{in.close();}return c.getValue();}
 public static void verifyZip(File f,Watch w)throws Exception{ZipFile z=new ZipFile(f);try{for(ZipEntry e:entries(z).values()){if(e.isDirectory())continue;CRC32 crc=new CRC32();long size=0;InputStream in=z.getInputStream(e);try{byte[] b=new byte[131072];int n;while((n=in.read(b))!=-1){check(w);crc.update(b,0,n);size+=n;}}finally{in.close();}require(size==e.getSize()&&crc.getValue()==e.getCrc(),"E_ZIP_CRC: "+e.getName());}}finally{z.close();}}
 public static final class Counting extends FilterOutputStream {public long count;public Counting(OutputStream o){super(o);}public void write(int b)throws IOException{out.write(b);count++;}public void write(byte[] b,int o,int n)throws IOException{out.write(b,o,n);count+=n;}}
}
