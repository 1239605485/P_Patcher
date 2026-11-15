package cn.minidayz.patcher;
import android.content.*;import android.database.*;import android.net.Uri;import android.os.ParcelFileDescriptor;import java.io.*;
public final class OutputProvider extends ContentProvider {
 public boolean onCreate(){return true;}
 private File result(Uri uri)throws FileNotFoundException{if(!"/latest.apk".equals(uri.getPath()))throw new FileNotFoundException();Jobs j=Jobs.get(getContext());File f=j.output;try{if(f==null||!f.isFile()||!f.getCanonicalPath().startsWith(new File(j.root,"outputs").getCanonicalPath()+File.separator))throw new FileNotFoundException();}catch(IOException e){throw new FileNotFoundException();}return f;}
 public ParcelFileDescriptor openFile(Uri uri,String mode)throws FileNotFoundException{if(!"r".equals(mode))throw new FileNotFoundException();return ParcelFileDescriptor.open(result(uri),ParcelFileDescriptor.MODE_READ_ONLY);}
 public String getType(Uri uri){return "application/vnd.android.package-archive";}
 public Cursor query(Uri u,String[] projection,String selection,String[] args,String order){try{File f=result(u);MatrixCursor c=new MatrixCursor(new String[]{"_display_name","_size"});c.addRow(new Object[]{f.getName(),f.length()});return c;}catch(Exception e){return null;}}
 public Uri insert(Uri u,ContentValues v){throw new UnsupportedOperationException();}public int delete(Uri u,String s,String[] a){throw new UnsupportedOperationException();}public int update(Uri u,ContentValues v,String s,String[] a){throw new UnsupportedOperationException();}
}
