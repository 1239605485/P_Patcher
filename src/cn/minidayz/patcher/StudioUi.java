package cn.minidayz.patcher;

import android.app.*;
import android.content.*;
import android.graphics.*;
import android.graphics.drawable.*;
import android.view.*;
import android.widget.*;

/** Shared offline shell for APK creation, live progress and local tools. */
public final class StudioUi {
 public final Activity a;
 public final boolean dark;
 public final int ink,muted,bg,card,line,accent=0xff168779;
 public LinearLayout body;
 private ScrollView scroll;
 private TextView title,subtitle;
 private Button[] tabs;
 public interface Nav{void select(int tab);}

 public StudioUi(Activity a){
  this.a=a;dark=(a.getResources().getConfiguration().uiMode&0x30)==0x20;
  ink=dark?0xffeef5f4:0xff153831;muted=dark?0xffa7beb9:0xff637d76;
  bg=dark?0xff0f1c1a:0xfff1f5f2;card=dark?0xff192b27:Color.WHITE;line=dark?0xff29433c:0xffe0ebe5;
 }
 public int dp(int n){return (int)(n*a.getResources().getDisplayMetrics().density+.5f);}
 public GradientDrawable shape(int color,int radius){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));return d;}

 public LinearLayout mount(int selected,final Nav nav){
  LinearLayout frame=new LinearLayout(a);frame.setOrientation(LinearLayout.VERTICAL);frame.setBackgroundColor(bg);
  a.getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
  frame.setFitsSystemWindows(true);
  LinearLayout heading=new LinearLayout(a);heading.setOrientation(LinearLayout.VERTICAL);heading.setPadding(dp(20),dp(12),dp(20),dp(8));
  TextView brand=text("P PATCHER  /  本地安装工具",11,accent);brand.setTypeface(null,Typeface.BOLD);heading.addView(brand);
  title=text("",25,ink);title.setTypeface(null,Typeface.BOLD);subtitle=text("",12,muted);heading.addView(title);heading.addView(subtitle);frame.addView(heading);
  scroll=new ScrollView(a);scroll.setFillViewport(true);body=new LinearLayout(a);body.setOrientation(LinearLayout.VERTICAL);
  body.setPadding(dp(16),dp(8),dp(16),dp(18));scroll.addView(body);frame.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
  LinearLayout navBar=new LinearLayout(a);navBar.setPadding(dp(10),dp(7),dp(10),dp(5));navBar.setBackgroundColor(card);
  tabs=new Button[3];String[] labels={"制作 APK","任务窗口","工具"};
  for(int i=0;i<3;i++){
   final int tab=i;Button b=new Button(a);b.setText(labels[i]);b.setTextSize(13);b.setAllCaps(false);b.setMinWidth(0);b.setMinimumWidth(0);b.setPadding(dp(4),0,dp(4),0);
   navBar.addView(b,new LinearLayout.LayoutParams(0,dp(48),1));b.setOnClickListener(new View.OnClickListener(){public void onClick(View v){nav.select(tab);}});tabs[i]=b;
  }
  frame.addView(navBar);a.setContentView(frame);frame.requestFitSystemWindows();select(selected);return body;
 }
 public void scrollToTop(){if(scroll!=null)scroll.post(new Runnable(){public void run(){scroll.scrollTo(0,0);}});}
 public void select(int i){
  if(i<0||i>=tabs.length)i=0;
  for(int k=0;k<3;k++){tabs[k].setTextColor(k==i?Color.WHITE:muted);tabs[k].setBackgroundDrawable(shape(k==i?accent:card,12));}
  title.setText(new String[]{"把插件装进游戏","每一步，都看得见","管理与诊断"}[i]);
  subtitle.setText(new String[]{"添加文件，确认版本，然后生成。","检查、处理、签名与输出，集中查看。","签名、引擎和日志，按需使用。"}[i]);
 }
 public TextView text(String s,int size,int color){TextView t=new TextView(a);t.setText(s);t.setTextSize(size);t.setTextColor(color);t.setPadding(0,dp(4),0,dp(6));t.setLineSpacing(dp(2),1);return t;}
 public LinearLayout card(LinearLayout parent,String name,String description){
  LinearLayout p=new LinearLayout(a);p.setOrientation(LinearLayout.VERTICAL);p.setPadding(dp(16),dp(14),dp(16),dp(16));p.setBackgroundDrawable(shape(card,18));
  LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.bottomMargin=dp(12);parent.addView(p,lp);
  if(name.length()>0){TextView h=text(name,17,ink);h.setTypeface(null,Typeface.BOLD);p.addView(h);}
  if(description.length()>0)p.addView(text(description,12,muted));return p;
 }
 public void paintButton(Button b,boolean primary){b.setTextColor(primary?Color.WHITE:ink);b.setTextSize(14);b.setAllCaps(false);b.setBackgroundDrawable(shape(primary?accent:line,11));b.setMinHeight(dp(48));}
 public Button button(LinearLayout p,String label,boolean primary,View.OnClickListener click){
  Button b=new Button(a);b.setText(label);b.setTextSize(14);b.setAllCaps(false);b.setTextColor(primary?Color.WHITE:ink);
  b.setPadding(dp(10),dp(8),dp(10),dp(8));b.setMinHeight(dp(48));b.setBackgroundDrawable(shape(primary?accent:line,11));
  LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.topMargin=dp(6);lp.bottomMargin=dp(4);p.addView(b,lp);if(click!=null)b.setOnClickListener(click);return b;
 }
 public void field(EditText e){e.setTextColor(ink);e.setHintTextColor(muted);e.setTextSize(15);e.setPadding(dp(12),dp(12),dp(12),dp(12));e.setBackgroundDrawable(shape(bg,10));LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.topMargin=dp(6);lp.bottomMargin=dp(8);e.setLayoutParams(lp);}
 public static void open(Activity a,int tab){Intent i=new Intent(a,MainActivity.class);i.putExtra("studio_tab",tab);i.addFlags(Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);a.startActivity(i);}
}
