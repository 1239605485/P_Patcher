package cn.minidayz.patcher;
import java.io.*;
public final class InventoryCli {public static void main(String[] args)throws Exception{System.out.println(ContentMatch.inventory(new File(args[0]),FilesEx.QUIET).toString());}}
