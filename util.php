<?php
function tg($method, $data = []) {
    $url = "https://api.telegram.org/bot" . BOT_TOKEN . "/" . $method;
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $data,
        CURLOPT_TIMEOUT => 30,
    ]);
    $res = curl_exec($ch);
    curl_close($ch);
    return json_decode($res ?: "{}", true);
}

function sendMessage($chat_id, $text, $keyboard = null, $reply_to = null) {
    $d = ["chat_id"=>$chat_id, "text"=>$text, "parse_mode"=>"HTML"];
    if ($keyboard) $d["reply_markup"] = json_encode($keyboard, JSON_UNESCAPED_UNICODE);
    if ($reply_to) $d["reply_to_message_id"] = $reply_to;
    return tg("sendMessage", $d);
}
function editMessage($chat_id, $message_id, $text, $keyboard = null) {
    $d=["chat_id"=>$chat_id,"message_id"=>$message_id,"text"=>$text,"parse_mode"=>"HTML"];
    if ($keyboard) $d["reply_markup"]=json_encode($keyboard,JSON_UNESCAPED_UNICODE);
    return tg("editMessageText",$d);
}
function answerCb($id,$text="") { return tg("answerCallbackQuery",["callback_query_id"=>$id,"text"=>$text]); }
function isGroup($type) { return in_array($type,["group","supergroup"]); }
function isSudo($id) { return (string)$id === SUDO_ID; }

function readJson($name,$default=[]) {
    $f=DATA_DIR."/".$name.".json";
    if(!file_exists($f)) return $default;
    $x=json_decode(file_get_contents($f),true);
    return is_array($x)?$x:$default;
}
function writeJson($name,$data) {
    file_put_contents(DATA_DIR."/".$name.".json",json_encode($data,JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT),LOCK_EX);
}
function userName($u) {
    $n=trim(($u["first_name"]??"")." ".($u["last_name"]??""));
    return $n!==""?$n:"بدون اسم";
}
function targetFromMessage($m) {
    if(isset($m["reply_to_message"]["from"])) return $m["reply_to_message"]["from"];
    return null;
}
function extractTarget($m) {
    $t=targetFromMessage($m);
    if($t) return ["id"=>$t["id"],"name"=>userName($t),"username"=>$t["username"]??""];
    $text=trim($m["text"]??"");
    $parts=preg_split('/\s+/u',$text);
    $arg=$parts[1]??"";
    if($arg==="") return null;
    if(ctype_digit(ltrim($arg,"-"))) return ["id"=>$arg,"name"=>$arg,"username"=>""];
    return ["id"=>$arg,"name"=>$arg,"username"=>ltrim($arg,"@")];
}
function getChatMember($chat,$user){ return tg("getChatMember",["chat_id"=>$chat,"user_id"=>$user]); }
function canManage($chat,$user) {
    $r=getChatMember($chat,$user);
    $s=$r["result"]["status"]??"";
    return in_array($s,["creator","administrator"]);
}
function botAdmin($chat) {
    $me=tg("getMe"); $id=$me["result"]["id"]??0;
    return canManage($chat,$id);
}
function restrictUser($chat,$user,$until=0,$canSend=false) {
    return tg("restrictChatMember",[
        "chat_id"=>$chat,"user_id"=>$user,
        "permissions"=>json_encode([
            "can_send_messages"=>$canSend,
            "can_send_audios"=>$canSend,
            "can_send_documents"=>$canSend,
            "can_send_photos"=>$canSend,
            "can_send_videos"=>$canSend,
            "can_send_video_notes"=>$canSend,
            "can_send_voice_notes"=>$canSend,
            "can_send_polls"=>$canSend,
            "can_send_other_messages"=>$canSend,
            "can_add_web_page_previews"=>$canSend,
        ]),
        "use_independent_chat_permissions"=>true,
        "until_date"=>$until
    ]);
}
function commandAliases($cmd) {
    $map=[
      "تفعيل"=>"add","شحن"=>"charge","فحص"=>"check","ترقية"=>"vip","عادية"=>"nvip",
      "شحن_مدفوع"=>"chargevip","فحص_مدفوعة"=>"checkvip",
      "رفع_مدير"=>"setmanager","ازالة_مدير"=>"remmanger","المدراء"=>"mangers",
      "رفع_مشرف"=>"setadmin","ازالة_مشرف"=>"remadmin","المشرفين"=>"admins",
      "طرد"=>"kick","حظر"=>"ban","الغاء_حظر"=>"unban","المحظورين"=>"banlist",
      "كتم"=>"mute","كتم_مؤقت"=>"tmute","الغاء_كتم"=>"unmute","المكتومين"=>"mutelist",
      "تحذير"=>"warn","الغاء_التحذير"=>"unwarn","الغاء_التحذيرات"=>"unwarns",
      "الحالة"=>"status","تعيين_التحذيرات"=>"setwarns","حظر_مؤقت"=>"tban",
      "تحديد_رسائل"=>"susermsg","اعدادات"=>"settings",
    ];
    return $map[$cmd]??$cmd;
}
?>
