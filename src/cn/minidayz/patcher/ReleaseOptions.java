package cn.minidayz.patcher;
public final class ReleaseOptions {
 public final String name,version;public final int code;
 public ReleaseOptions(String n,String v,int c)throws Exception{name=valid(n,80,"软件名称");version=valid(v,80,"版本名称");FilesEx.require(c>0&&c<=2100000000,"E_VERSION_CODE: 内部版本代码超出 Android 范围");code=c;}
 private static String valid(String s,int max,String what)throws Exception{FilesEx.require(s!=null&&s.trim().length()>0&&s.trim().length()<=max,"E_RELEASE_TEXT: "+what+"须为 1 至 "+max+" 个字符");s=s.trim();for(int i=0;i<s.length();i++)FilesEx.require(!Character.isISOControl(s.charAt(i)),"E_RELEASE_TEXT: "+what+"不能含换行或控制字符");return s;}
 public static int requestedCode(String text)throws Exception{
  if(text==null||text.trim().length()==0)return 0;
  FilesEx.require(text.trim().matches("[0-9]+"),"E_VERSION_CODE: 版本代码只能是正整数");
  long n;try{n=Long.parseLong(text.trim());}catch(NumberFormatException e){throw new java.io.IOException("E_VERSION_CODE: 版本代码超出范围");}
  FilesEx.require(n>0&&n<=2100000000L,"E_VERSION_CODE: 版本代码须在 1 至 2100000000 之间");return (int)n;
 }
 public static int resolveCode(String text,int profile,int installed,int previous)throws Exception{
  int min=nextCode(profile,installed,previous),requested=requestedCode(text);
  FilesEx.require(requested==0||requested>=min,"E_VERSION_CODE: 为保证覆盖升级，版本代码至少为 "+min);
  return requested==0?min:requested;
 }
 public static int nextCode(int profile,int installed,int previous)throws Exception{long n=Math.max((long)profile,Math.max((long)installed+1,(long)previous+1));FilesEx.require(n>0&&n<=2100000000L,"E_VERSION_CODE: 内部版本代码已达上限");return (int)n;}
}
