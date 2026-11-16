package cn.minidayz.patcher;

/** Builds bounded evidence blocks so AI requests do not resend unlimited logs. */
public final class AiContext {
 private AiContext() {}

 public static String compact(String label,String value,int limit){
  if(value==null)value="";
  if(value.length()<=limit)return label+"\n"+value;
  int head=Math.max(1,limit*2/3),tail=Math.max(1,limit-head);
  return label+"\n"+value.substring(0,head)+"\n...[内容已截断，完整证据保留在本地]...\n"+value.substring(value.length()-tail);
 }
}
