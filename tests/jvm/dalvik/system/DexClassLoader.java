package dalvik.system;
/** JVM test bridge only. APK build never includes tests/. Android uses real DexClassLoader. */
public class DexClassLoader extends java.net.URLClassLoader {
 public DexClassLoader(String dex,String optimized,String libs,ClassLoader parent)throws Exception{super(new java.net.URL[]{new java.io.File(System.getProperty("test.engine.jar")).toURI().toURL()},parent);}
}
