package cn.minidayz.patcher;
import org.json.*;
/** Deterministic action gate kept independent of UI, Android and model output. */
public final class AutonomyDecision {
 public static JSONObject decide(boolean compatible,boolean key,boolean logAllowed,boolean errorMarkers,boolean rule)throws Exception{String code="",reason="";if(!compatible){code="E_LOCAL_COMPATIBILITY";reason="当前输入与插件不兼容，需要对应版本适配包";}else if(!logAllowed){code="E_LOCAL_LOG_IDENTITY";reason="日志归属未知或与当前项目冲突，停止自动修改";}else if(errorMarkers&&!rule){code="E_LOCAL_NO_REPAIR";reason="已发现错误标记，但没有已实测规则；交AI或人工分析";}else if(!key){code="E_KEY_MISSING";reason="自动构建需要原签名文件";}return new JSONObject().put("allowed",code.length()==0).put("error_code",code).put("reason",code.length()==0?(rule?"复用完全匹配的实测规则后构建":"按兼容插件构建，不宣称修复日志错误"):reason);}
}
