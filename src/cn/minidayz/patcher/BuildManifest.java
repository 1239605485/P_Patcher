package cn.minidayz.patcher;

/** Supplies a per-build identifier for the receipt embedded in the output APK. */
public final class BuildManifest {
 private BuildManifest() {}
 public static String id(){return "build-"+System.currentTimeMillis()+"-"+Long.toHexString(System.nanoTime());}
}
