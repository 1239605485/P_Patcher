package cn.minidayz.patcher;
public final class ReleaseOptions {
 public final String name,version;public final int code;
 public ReleaseOptions(String n,String v,int c)throws Exception{name=valid(n,80,"软件名称");version=valid(v,80,"版本名称");FilesEx.require(c>0&&c<=2100000000,"E_VERSION_CODE: 内部版本代码超出 Android 范围");code=c;}
 private static String valid(String s,int max,String what)throws Exception{FilesEx.require(s!=null&&s.trim().length()>0&&s.trim().length()<=max,"E_RELEASE_TEXT: "+what+"须为 1 至 "+max+" 个字符");s=s.trim();for(int i=0;i<s.length();i++)FilesEx.require(!Character.isISOControl(s.charAt(i)),"E_RELEASE_TEXT: "+what+"不能含换行或控制字符");return s;}
 public static int nextCode(int profile,int installed,int previous)throws Exception{long n=Math.max((long)profile,Math.max((long)installed+1,(long)previous+1));FilesEx.require(n>0&&n<=2100000000L,"E_VERSION_CODE: 内部版本代码已达上限");return (int)n;}
}
