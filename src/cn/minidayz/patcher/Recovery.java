package cn.minidayz.patcher;
import java.io.*;
public final class Recovery {
 /** Clean only known unfinished work. Inputs, keys, outputs and history are retained. */
 public static void clean(File root){FilesEx.deleteTree(new File(root,"jobs"));for(String n:new String[]{"import.pending","diagnostic.pending.zip","history.pending"})new File(root,n).delete();}
}
