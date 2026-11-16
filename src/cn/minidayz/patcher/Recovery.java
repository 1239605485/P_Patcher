package cn.minidayz.patcher;
import java.io.*;
public final class Recovery {
 /** Clean only known unfinished work. Inputs, keys, outputs and history are retained. */
 public static void clean(File root){FilesEx.deleteTree(new File(root,"jobs"));File store=new File(root,"features"),backup=new File(root,"features.previous");if(!store.exists()&&backup.exists())backup.renameTo(store);else if(store.exists())FilesEx.deleteTree(backup);FilesEx.deleteTree(new File(root,"feature-import"));FilesEx.deleteTree(new File(root,"feature-selection"));File[] children=root.listFiles();if(children!=null)for(File f:children)if(f.getName().startsWith("verify-parts-"))FilesEx.deleteTree(f);for(String n:new String[]{"import.pending","diagnostic.pending.zip","history.pending"})new File(root,n).delete();}
}
