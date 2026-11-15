package cn.minidayz.patcher;
import java.io.IOException;
/** org.json accepts unquoted values and trailing commas; edited JSON must be strict. */
public final class StrictJson {
 private final String s;private int at;private StrictJson(String text){s=text;}
 public static void check(String s)throws Exception{StrictJson p=new StrictJson(s);p.value(0);p.ws();p.need(p.at==s.length());}
 void need(boolean b)throws IOException{FilesEx.require(b,"E_AI_JSON: 修改后的 JSON 语法无效");}void ws(){while(at<s.length()&&" \r\n\t".indexOf(s.charAt(at))>=0)at++;}char peek(){return at<s.length()?s.charAt(at):'\0';}
 void string()throws Exception{need(peek()=='"');at++;while(at<s.length()){char c=s.charAt(at++);if(c=='"')return;need(c>=32);if(c=='\\'){need(at<s.length());char e=s.charAt(at++);if(e=='u'){for(int i=0;i<4;i++){need(at<s.length()&&Character.digit(s.charAt(at++),16)>=0);}}else need("\"\\/bfnrt".indexOf(e)>=0);}}need(false);}
 void value(int depth)throws Exception{need(depth<80);ws();char c=peek();if(c=='"'){string();return;}if(c=='{'||c=='['){at++;ws();char end=c=='{'?'}':']';if(peek()==end){at++;return;}while(true){if(c=='{'){string();ws();need(peek()==':');at++;}value(depth+1);ws();if(peek()==end){at++;return;}need(peek()==',');at++;ws();}}if(s.startsWith("true",at)){at+=4;return;}if(s.startsWith("false",at)){at+=5;return;}if(s.startsWith("null",at)){at+=4;return;}if(c=='-')at++;need(peek()>='0'&&peek()<='9');if(peek()=='0')at++;else while(peek()>='0'&&peek()<='9')at++;if(peek()=='.'){at++;int start=at;while(peek()>='0'&&peek()<='9')at++;need(at>start);}if(peek()=='e'||peek()=='E'){at++;if(peek()=='+'||peek()=='-')at++;int start=at;while(peek()>='0'&&peek()<='9')at++;need(at>start);}}
}
