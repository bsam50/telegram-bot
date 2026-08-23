<?php
function ensureChat($m) {
    $db=readJson("groups",[]);
    $id=(string)$m["chat"]["id"];
    if(!isset($db[$id])) {
        $db[$id]=[
          "id"=>$m["chat"]["id"],"title"=>$m["chat"]["title"]??"",
          "vip"=>false,"expires"=>0,"paid_expires"=>0,
          "welcome"=>true,"delete_old_welcome"=>true,"kick_bots"=>false,"rules"=>true,
          "rules_button"=>true,"warn_limit"=>4,"warn_action"=>"kick",
          "control_place"=>"private","locks"=>[],"alerts"=>[],"managers"=>[],"admins"=>[],
          "warns"=>[],"muted"=>[],"message_limits"=>[]
        ];
        writeJson("groups",$db);
    } else {
        $db[$id]["title"]=$m["chat"]["title"]??($db[$id]["title"]??"");
        writeJson("groups",$db);
    }
}
function groupData($id) {
    $db=readJson("groups",[]);
    return $db[(string)$id]??null;
}
function saveGroup($id,$g) {
    $db=readJson("groups",[]);
    $db[(string)$id]=$g; writeJson("groups",$db);
}
function isPrivileged($m) {
    $uid=$m["from"]["id"]??0; $cid=$m["chat"]["id"];
    if(isSudo($uid)) return true;
    $g=groupData($cid);
    if(!$g) return canManage($cid,$uid);
    if(in_array((string)$uid,array_map("strval",$g["managers"]??[]))) return true;
    if(in_array((string)$uid,array_map("strval",$g["admins"]??[]))) return true;
    return canManage($cid,$uid);
}
function requireGroup($m) {
    if(!isGroup($m["chat"]["type"])) { sendMessage($m["chat"]["id"],"⚠️ هذا الأمر يعمل داخل المجموعات فقط."); return false; }
    if(!botAdmin($m["chat"]["id"])) { sendMessage($m["chat"]["id"],"⚠️ يجب رفع البوت مشرفاً مع صلاحيات الحظر والتقييد."); return false; }
    return true;
}
function handleCommand($cmd,$m) {
    $cid=$m["chat"]["id"]; $uid=$m["from"]["id"]; $isG=isGroup($m["chat"]["type"]);
    if($cmd==="start") { startPrivate($m); return; }
    if($cmd==="settings") { settingsMenu($m); return; }

    if(in_array($cmd,["add","charge","check","vip","nvip","chargevip","checkvip"])) { subscriptionCommand($cmd,$m); return; }

    if(in_array($cmd,["setmanager","remmanger","mangers","setadmin","remadmin","admins"])) {
        rankCommand($cmd,$m); return;
    }

    if(in_array($cmd,["kick","ban","unban","banlist","mute","tmute","unmute","mutelist","warn","unwarn","unwarns","status","setwarns","tban","susermsg"])) {
        moderationCommand($cmd,$m); return;
    }

    if($cmd==="ربط") { linkAlerts($m); return; }
}
function startPrivate($m) {
    if($m["chat"]["type"]!=="private") return;
    sendMessage($m["chat"]["id"],
      "👋 أهلاً بك في <b>Botar</b>\n\n🛡 بوت حماية وإدارة للمجموعات.\nاختر من القائمة:",
      ["inline_keyboard"=>[
        [["text"=>"🤖 طلب البوت","callback_data"=>"request_bot"],["text"=>"🆘 الدعم","callback_data"=>"support"]]
      ]]);
}
function subscriptionCommand($cmd,$m) {
    if(!isGroup($m["chat"]["type"])) { sendMessage($m["chat"]["id"],"⚠️ هذا الأمر للمجموعات."); return; }
    if($cmd==="check") {
        $g=groupData($m["chat"]["id"]); $left=max(0,($g["expires"]??0)-time());
        sendMessage($m["chat"]["id"],"🔎 المتبقي: <b>".ceil($left/86400)."</b> يوم.");
        return;
    }
    if(!isSudo($m["from"]["id"])) { sendMessage($m["chat"]["id"],"⛔️ هذا الأمر للمطور فقط."); return; }
    $g=groupData($m["chat"]["id"]); if(!$g) return;
    if($cmd==="vip"||$cmd==="nvip") { $g["vip"]=($cmd==="vip"); saveGroup($m["chat"]["id"],$g); sendMessage($m["chat"]["id"],$g["vip"]?"⭐️ تم ترقية المجموعة إلى VIP.":"✅ تم إرجاع المجموعة إلى عادية."); return; }
    $days=["add"=>30,"charge"=>30,"chargevip"=>30][$cmd]??30;
    $g["expires"]=max(time(),$g["expires"]??0)+$days*86400; saveGroup($m["chat"]["id"],$g);
    sendMessage($m["chat"]["id"],"✅ تم الشحن لمدة <b>$days</b> يوم.");
}
function rankCommand($cmd,$m) {
    if(!requireGroup($m)) return;
    if(!isPrivileged($m)) { sendMessage($m["chat"]["id"],"⛔️ ليس لديك صلاحية."); return; }
    $g=groupData($m["chat"]["id"]);
    if(in_array($cmd,["mangers","admins"])) {
        $key=$cmd==="mangers"?"managers":"admins"; $arr=$g[$key]??[];
        $out=$cmd==="mangers"?"👑 المدراء:\n":"🛡 المشرفين:\n";
        foreach($arr as $id) $out.="• <code>$id</code>\n";
        sendMessage($m["chat"]["id"],$out); return;
    }
    if(!isSudo($m["from"]["id"]) && !canManage($m["chat"]["id"],$m["from"]["id"])) { sendMessage($m["chat"]["id"],"⛔️ لا يمكنك تعديل الرتب."); return; }
    $t=extractTarget($m); if(!$t){sendMessage($m["chat"]["id"],"⚠️ استخدم الأمر بالرد على العضو أو أرسل ID/معرف.");return;}
    $key=in_array($cmd,["setmanager","remmanger"])?"managers":"admins";
    $add=in_array($cmd,["setmanager","setadmin"]);
    $g[$key]=$g[$key]??[];
    if($add && !in_array((string)$t["id"],array_map("strval",$g[$key]))) $g[$key][]=(string)$t["id"];
    if(!$add) $g[$key]=array_values(array_filter($g[$key],fn($x)=>(string)$x!==(string)$t["id"]));
    saveGroup($m["chat"]["id"],$g);
    if($add) {
        $rights=$key==="managers"?["can_manage_chat"=>true,"can_delete_messages"=>true,"can_restrict_members"=>true,"can_invite_users"=>true]:["can_delete_messages"=>true,"can_restrict_members"=>true,"can_invite_users"=>true];
        tg("promoteChatMember",["chat_id"=>$m["chat"]["id"],"user_id"=>$t["id"],"can_manage_chat"=>$rights["can_manage_chat"]??false,"can_delete_messages"=>$rights["can_delete_messages"]??true,"can_restrict_members"=>true,"can_invite_users"=>true,"can_pin_messages"=>true]);
    } else {
        tg("promoteChatMember",["chat_id"=>$m["chat"]["id"],"user_id"=>$t["id"],"can_manage_chat"=>false,"can_delete_messages"=>false,"can_restrict_members"=>false,"can_invite_users"=>false,"can_pin_messages"=>false]);
    }
    sendMessage($m["chat"]["id"],$add?"✅ تم رفع العضو.":"✅ تم إزالة رتبة العضو.");
}
function moderationCommand($cmd,$m) {
    if(!requireGroup($m)) return;
    if(!isPrivileged($m)) { sendMessage($m["chat"]["id"],"⛔️ ليس لديك صلاحية."); return; }
    $cid=$m["chat"]["id"]; $g=groupData($cid); $t=extractTarget($m);
    if(in_array($cmd,["banlist","mutelist"])) {
        $key=$cmd==="banlist"?"banned":"muted"; $db=readJson($key,[]);
        $arr=$db[(string)$cid]??[];
        $out=$cmd==="banlist"?"🚫 المحظورين:\n":"🔇 المكتومين:\n";
        foreach($arr as $id=>$v) $out.="• <code>$id</code>\n";
        sendMessage($cid,$out); return;
    }
    if(!$t){sendMessage($cid,"⚠️ يجب أن ترد على رسالة العضو أو تضع المعرف/ID.");return;}
    $id=$t["id"];
    if(in_array($cmd,["kick","ban","unban","mute","tmute","unmute"])) {
        if($cmd==="kick") tg("banChatMember",["chat_id"=>$cid,"user_id"=>$id]); 
        if($cmd==="ban"||$cmd==="tban") tg("banChatMember",["chat_id"=>$cid,"user_id"=>$id,"until_date"=>($cmd==="tban"?time()+3600:0)]);
        if($cmd==="unban") tg("unbanChatMember",["chat_id"=>$cid,"user_id"=>$id,"only_if_banned"=>true]);
        if($cmd==="mute"||$cmd==="tmute") restrictUser($cid,$id,$cmd==="tmute"?time()+3600:0,false);
        if($cmd==="unmute") restrictUser($cid,$id,0,true);
        $db=readJson($cmd==="ban"||$cmd==="tban"||$cmd==="unban"?"banned":"muted",[]);
        if(!isset($db[(string)$cid])) $db[(string)$cid]=[];
        if(in_array($cmd,["ban","tban","mute","tmute"])) $db[(string)$cid][(string)$id]=["name"=>$t["name"],"time"=>time()];
        else unset($db[(string)$cid][(string)$id]);
        writeJson($cmd==="ban"||$cmd==="tban"||$cmd==="unban"?"banned":"muted",$db);
        $labels=["kick"=>"طرد","ban"=>"حظر","unban"=>"إلغاء الحظر","mute"=>"كتم","tmute"=>"كتم مؤقت","unmute"=>"إلغاء الكتم"];
        sendMessage($cid,"✅ تم {$labels[$cmd]} العضو.");
        return;
    }
    $warns=$g["warns"]??[];
    if($cmd==="warn") {
        $warns[(string)$id]=($warns[(string)$id]??0)+1; $g["warns"]=$warns; saveGroup($cid,$g);
        $n=$warns[(string)$id]; sendMessage($cid,"⚠️ تم تحذير العضو.\nالتحذيرات: <b>$n/".($g["warn_limit"]??4)."</b>");
        if($n>=($g["warn_limit"]??4)) {
            $act=$g["warn_action"]??"kick";
            if($act==="ban") tg("banChatMember",["chat_id"=>$cid,"user_id"=>$id]);
            elseif($act==="mute") restrictUser($cid,$id,0,false);
            else tg("banChatMember",["chat_id"=>$cid,"user_id"=>$id]);
            $g["warns"][$id]=0; saveGroup($cid,$g);
        }
    } elseif($cmd==="unwarn") {
        $g["warns"][(string)$id]=max(0,($g["warns"][(string)$id]??0)-1); saveGroup($cid,$g); sendMessage($cid,"✅ تم إلغاء تحذير واحد.");
    } elseif($cmd==="unwarns") {
        $g["warns"][(string)$id]=0; saveGroup($cid,$g); sendMessage($cid,"✅ تم إلغاء جميع التحذيرات.");
    } elseif($cmd==="status") {
        $n=$g["warns"][(string)$id]??0; sendMessage($cid,"👤 العضو: <b>".htmlspecialchars($t["name"])."</b>\n⚠️ التحذيرات: <b>$n/".($g["warn_limit"]??4)."</b>");
    } elseif($cmd==="setwarns") {
        $parts=preg_split('/\s+/u',trim($m["text"]??"")); $n=(int)($parts[1]??4); $g["warn_limit"]=max(1,$n); saveGroup($cid,$g); sendMessage($cid,"✅ تم تعيين الحد الأقصى للتحذيرات إلى <b>".$g["warn_limit"]."</b>.");
    } elseif($cmd==="susermsg") {
        sendMessage($cid,"ℹ️ نظام تحديد الرسائل محفوظ ضمن إعدادات الحماية ويمكن تفعيله من لوحة الإعدادات.");
    }
}
function settingsMenu($m) {
    if(!isGroup($m["chat"]["type"])) { sendMessage($m["chat"]["id"],"⚠️ أرسل /اعدادات داخل المجموعة."); return; }
    if(!isPrivileged($m)) { sendMessage($m["chat"]["id"],"⛔️ ليس لديك صلاحية."); return; }
    $cid=$m["chat"]["id"];
    $kb=["inline_keyboard"=>[
      [["text"=>"🔵 مكان التحكم","callback_data"=>"set_control"],["text"=>"🔵 إعدادات عامة","callback_data"=>"general"]],
      [["text"=>"🔵 إعدادات القفل","callback_data"=>"locks"]],
      [["text"=>"🔵 الإشعارات","callback_data"=>"alerts"]],
      [["text"=>"⛔️ خروج","callback_data"=>"close"]]
    ]];
    sendMessage($cid,"⚙️ <b>إعدادات المجموعة</b>\nاختر القسم:",$kb);
}
function settingsGeneral($cid,$mid) {
    $g=groupData($cid); $on="✅"; $off="☑️";
    $kb=["inline_keyboard"=>[
      [["text"=>"رسالة الترحيب", "callback_data"=>"toggle_welcome"],["text"=>$g["welcome"]?$on:$off,"callback_data"=>"toggle_welcome"]],
      [["text"=>"حذف آخر رسالة ترحيب","callback_data"=>"toggle_deletewelcome"],["text"=>$g["delete_old_welcome"]?$on:$off,"callback_data"=>"toggle_deletewelcome"]],
      [["text"=>"طرد البوتات","callback_data"=>"toggle_kickbots"],["text"=>$g["kick_bots"]?$on:$off,"callback_data"=>"toggle_kickbots"]],
      [["text"=>"القوانين","callback_data"=>"toggle_rules"],["text"=>$g["rules"]?$on:$off,"callback_data"=>"toggle_rules"]],
      [["text"=>"ترحيب مع زر القوانين","callback_data"=>"toggle_rulesbutton"],["text"=>$g["rules_button"]?$on:$off,"callback_data"=>"toggle_rulesbutton"]],
      [["text"=>"عدد التحذيرات","callback_data"=>"warnlimit"]],
      [["text"=>"الإجراء","callback_data"=>"warnaction"]],
      [["text"=>"↩️ رجوع","callback_data"=>"settings"]]
    ]];
    editMessage($cid,$mid,"⚙️ <b>إعدادات عامة</b>",$kb);
}
function settingsLocks($cid,$mid) {
    $g=groupData($cid); $items=["photos"=>"الصور","video"=>"الفيديو","voice"=>"التسجيلات","audio"=>"الصوتيات","stickers"=>"الملصقات","animations"=>"الصور المتحركة","video_notes"=>"تسجيلات الفيديو","links"=>"الروابط","telegram_links"=>"الإعلانات","forward"=>"التوجيه","contacts"=>"جهات الاتصال","markdown"=>"الماركداون","inline"=>"الانلاين","games"=>"الألعاب","locations"=>"المواقع","mentions"=>"التاق","hashtags"=>"الهاشتاق","alerts"=>"الإشعارات"];
    $kb=[]; foreach($items as $k=>$v){$on=($g["locks"][$k]??false)?"🚫":"☑️"; $kb[]=[["text"=>$v,"callback_data"=>"lock_$k"],["text"=>$on,"callback_data"=>"lock_$k"]];}
    $kb[]=[["text"=>"↩️ رجوع","callback_data"=>"settings"]];
    editMessage($cid,$mid,"🔒 <b>إعدادات القفل</b>",["inline_keyboard"=>$kb]);
}
function alertsMenu($cid,$mid) {
    $g=groupData($cid); $items=["spam"=>"التكرار","unban"=>"فك الحظر","pin"=>"تثبيت رسالة","name"=>"تغيير اسم المجموعة","warn"=>"تحذير","photo"=>"تغيير صورة المجموعة","ban"=>"حظر","new"=>"عضو جديد","unwarn"=>"مسح التحذير","kick"=>"طرد","rules"=>"القوانين","welcome"=>"الترحيب"];
    $kb=[]; foreach($items as $k=>$v){$on=($g["alerts"][$k]??false)?"✅":"☑️"; $kb[]=[["text"=>$v,"callback_data"=>"alert_$k"],["text"=>$on,"callback_data"=>"alert_$k"]];}
    $kb[]=[["text"=>"↩️ رجوع","callback_data"=>"settings"]];
    editMessage($cid,$mid,"🔔 <b>إعدادات الإشعارات</b>",["inline_keyboard"=>$kb]);
}
function linkAlerts($m){ sendMessage($m["chat"]["id"],"🔗 لإعداد ربط الإشعارات بالقناة، أضف البوت مشرفاً في القناة ثم أعد توجيه أمر /ربط من المجموعة إلى القناة."); }
function moderateLocks($m) {
    if(!isGroup($m["chat"]["type"])) return;
    $g=groupData($m["chat"]["id"]); if(!$g) return;
    $lock=$g["locks"]??[]; $type="";
    if(isset($m["photo"])) $type="photos";
    elseif(isset($m["video"])) $type="video";
    elseif(isset($m["voice"])) $type="voice";
    elseif(isset($m["audio"])) $type="audio";
    elseif(isset($m["sticker"])) $type="stickers";
    elseif(isset($m["animation"])) $type="animations";
    elseif(isset($m["video_note"])) $type="video_notes";
    elseif(isset($m["contact"])) $type="contacts";
    elseif(isset($m["location"])) $type="locations";
    elseif(isset($m["forward_origin"]) || isset($m["forward_from"])) $type="forward";
    elseif(isset($m["text"]) && preg_match('/https?:\/\/|www\./iu',$m["text"])) $type="links";
    if($type && !empty($lock[$type])) {
        tg("deleteMessage",["chat_id"=>$m["chat"]["id"],"message_id"=>$m["message_id"]]);
    }
}
function handleCallback($cq,$cid,$mid,$uid,$data) {
    if($data==="support"){answerCb($cq["id"]); sendMessage($uid,"🆘 للدعم تواصل مع المطور.");return;}
    if($data==="request_bot"){answerCb($cq["id"]); sendMessage($uid,"🔗 أرسل رابط المجموعة التي تريد تفعيل البوت فيها.");return;}
    if(!isSudo($uid) && isGroup($cq["message"]["chat"]["type"]) && !isPrivileged($cq["message"])) {answerCb($cq["id"],"⛔️ لا تملك الصلاحية.");return;}
    answerCb($cq["id"]);
    if($data==="settings"){settingsMenu($cq["message"]);return;}
    if($data==="general"){settingsGeneral($cid,$mid);return;}
    if($data==="locks"){settingsLocks($cid,$mid);return;}
    if($data==="alerts"){alertsMenu($cid,$mid);return;}
    if($data==="close"){tg("deleteMessage",["chat_id"=>$cid,"message_id"=>$mid]);return;}
    if($data==="set_control"){editMessage($cid,$mid,"📍 <b>مكان التحكم</b>\nاختر مكان ظهور إعدادات المجموعة:",["inline_keyboard"=>[
      [["text"=>"📍 في المجموعة","callback_data"=>"control_group"],["text"=>"🔒 في الخاص","callback_data"=>"control_private"]],
      [["text"=>"↩️ رجوع","callback_data"=>"settings"]]
    ]]);return;}
    if(str_starts_with($data,"toggle_")) {
        $k=substr($data,7); $map=["welcome"=>"welcome","deletewelcome"=>"delete_old_welcome","kickbots"=>"kick_bots","rules"=>"rules","rulesbutton"=>"rules_button"];
        if(isset($map[$k])){$g=groupData($cid);$g[$map[$k]]=empty($g[$map[$k]]);saveGroup($cid,$g);settingsGeneral($cid,$mid);} return;
    }
    if($data==="warnlimit"){editMessage($cid,$mid,"⚠️ أرسل في المجموعة:\n<code>/setwarns 4</code>\nلتعيين الحد الأقصى للتحذيرات.",["inline_keyboard"=>[[["text"=>"↩️ رجوع","callback_data"=>"general"]]]]);return;}
    if($data==="warnaction"){editMessage($cid,$mid,"⚠️ اختر إجراء الوصول للحد الأقصى:",["inline_keyboard"=>[
      [["text"=>"طرد","callback_data"=>"action_kick"],["text"=>"حظر","callback_data"=>"action_ban"],["text"=>"كتم","callback_data"=>"action_mute"]],
      [["text"=>"↩️ رجوع","callback_data"=>"general"]]
    ]]);return;}
    if(str_starts_with($data,"action_")){$g=groupData($cid);$g["warn_action"]=substr($data,7);saveGroup($cid,$g);settingsGeneral($cid,$mid);return;}
    if(str_starts_with($data,"lock_")){$k=substr($data,5);$g=groupData($cid);$g["locks"][$k]=empty($g["locks"][$k]);saveGroup($cid,$g);settingsLocks($cid,$mid);return;}
    if(str_starts_with($data,"alert_")){$k=substr($data,6);$g=groupData($cid);$g["alerts"][$k]=empty($g["alerts"][$k]);saveGroup($cid,$g);alertsMenu($cid,$mid);return;}
    if(in_array($data,["control_group","control_private"])){$g=groupData($cid);$g["control_place"]=$data==="control_group"?"group":"private";saveGroup($cid,$g);settingsMenu($cq["message"]);return;}
}
?>
