<?php

/* =========================================================
   BOTAR - CORE COMMANDS
   يعتمد على config.php + util.php + index.php
   ========================================================= */


/* =========================
   أدوات البيانات
========================= */

function botarGroups() {
    return readJson("groups", []);
}

function botarSaveGroups($data) {
    writeJson("groups", $data);
}

function botarGroup($chatId, $create = true) {
    $groups = botarGroups();
    $id = (string)$chatId;

    if (!isset($groups[$id]) && $create) {
        $groups[$id] = [
            "id" => $chatId,
            "title" => "بدون اسم",
            "active" => true,
            "vip" => false,
            "expire" => 0,
            "welcome" => true,
            "welcome_delete" => false,
            "welcome_rules_button" => false,
            "rules" => "",
            "warn_limit" => 3,
            "warn_action" => "kick",
            "managers" => [],
            "admins" => [],
            "warns" => [],
            "banned" => [],
            "muted" => [],
            "locks" => [],
            "lock_actions" => [],
            "settings" => [],
            "channel" => null
        ];

        botarSaveGroups($groups);
    }

    return $groups[$id] ?? null;
}

function botarUpdateGroup($chatId, $data) {
    $groups = botarGroups();
    $groups[(string)$chatId] = $data;
    botarSaveGroups($groups);
}

function botarAddDays($chatId, $days, $vip = false) {
    $g = botarGroup($chatId);

    $now = time();

    if (($g["expire"] ?? 0) > $now) {
        $base = $g["expire"];
    } else {
        $base = $now;
    }

    $g["expire"] = $base + ($days * 86400);

    if ($vip) {
        $g["vip"] = true;
    }

    $g["active"] = true;

    botarUpdateGroup($chatId, $g);

    return $g["expire"];
}


/* =========================
   المجموعة
========================= */

function ensureChat($m) {
    $chat = $m["chat"] ?? [];

    if (!isset($chat["id"])) {
        return;
    }

    $id = $chat["id"];
    $g = botarGroup($id);

    if (!$g) {
        return;
    }

    $g["title"] = $chat["title"] ?? ($g["title"] ?? "بدون اسم");

    botarUpdateGroup($id, $g);
}


/* =========================
   الصلاحيات
========================= */

function botarIsSudo($id) {
    return isSudo($id);
}

function botarAssistants() {
    return readJson("assistants", []);
}

function botarIsAssistant($id) {
    $list = botarAssistants();

    foreach ($list as $x) {
        if ((string)($x["id"] ?? $x) === (string)$id) {
            return true;
        }
    }

    return false;
}

function botarIsDeveloper($id) {
    return botarIsSudo($id);
}

function botarIsManager($chatId, $id) {
    if (botarIsDeveloper($id) || botarIsAssistant($id)) {
        return true;
    }

    $g = botarGroup($chatId, false);

    if (!$g) {
        return false;
    }

    foreach (($g["managers"] ?? []) as $x) {
        if ((string)($x["id"] ?? $x) === (string)$id) {
            return true;
        }
    }

    return canManage($chatId, $id);
}

function botarIsAdmin($chatId, $id) {
    if (botarIsManager($chatId, $id)) {
        return true;
    }

    $g = botarGroup($chatId, false);

    if (!$g) {
        return false;
    }

    foreach (($g["admins"] ?? []) as $x) {
        if ((string)($x["id"] ?? $x) === (string)$id) {
            return true;
        }
    }

    return canManage($chatId, $id);
}

function botarRequireAdmin($m) {
    $chat = $m["chat"]["id"] ?? 0;
    $user = $m["from"]["id"] ?? 0;

    if (!botarIsAdmin($chat, $user)) {
        sendMessage($chat, "⛔️ هذا الأمر للمشرفين فقط.");
        return false;
    }

    return true;
}

function botarRequireManager($m) {
    $chat = $m["chat"]["id"] ?? 0;
    $user = $m["from"]["id"] ?? 0;

    if (!botarIsManager($chat, $user)) {
        sendMessage($chat, "⛔️ هذا الأمر للمديرين والمطور فقط.");
        return false;
    }

    return true;
}

function botarRequireDev($m) {
    $user = $m["from"]["id"] ?? 0;
    $chat = $m["chat"]["id"] ?? 0;

    if (!botarIsDeveloper($user)) {
        sendMessage($chat, "⛔️ هذا الأمر للمطور فقط.");
        return false;
    }

    return true;
}


/* =========================
   الهدف
========================= */

function botarTarget($m) {
    $target = extractTarget($m);

    if ($target) {
        return $target;
    }

    if (isset($m["reply_to_message"]["from"]["id"])) {
        $u = $m["reply_to_message"]["from"];

        return [
            "id" => $u["id"],
            "name" => userName($u),
            "username" => $u["username"] ?? ""
        ];
    }

    return null;
}


/* =========================
   أسماء الأوامر
========================= */

function botarNormalizeCommand($m) {

    $text = trim($m["text"] ?? "");

    if ($text === "") {
        return "";
    }

    $text = preg_replace('/^[\/!#]/u', '', $text);

    $parts = preg_split('/\s+/u', $text);

    $one = $parts[0] ?? "";
    $two = $parts[1] ?? "";

    $twoWord = trim($one . " " . $two);

    $map = [

        "رفع مدير" => "setmanager",
        "ازالة مدير" => "remmanger",
        "المدراء" => "mangers",

        "رفع مشرف" => "setadmin",
        "ازالة مشرف" => "remadmin",
        "المشرفين" => "admins",

        "الغاء حظر" => "unban",
        "كتم مؤقت" => "tmute",
        "الغاء كتم" => "unmute",
        "المكتومين" => "mutelist",

        "الغاء التحذير" => "unwarn",
        "الغاء التحذيرات" => "unwarns",
        "حظر مؤقت" => "tban",
        "تعيين التحذيرات" => "setwarns",
        "تحديد رسائل" => "susermsg",

        "شحن مدفوع" => "chargevip",
        "فحص مدفوعة" => "checkvip",

        "عادية" => "nvip",
        "اعدادات" => "settings",

        "تفعيل" => "add",
        "شحن" => "charge",
        "فحص" => "check",
        "ترقية" => "vip",

        "طرد" => "kick",
        "حظر" => "ban",
        "المحظورين" => "banlist",
        "كتم" => "mute",
        "تحذير" => "warn",
        "الحالة" => "status",

        "setmanager" => "setmanager",
        "remmanger" => "remmanger",
        "mangers" => "mangers",
        "setadmin" => "setadmin",
        "remadmin" => "remadmin",
        "admins" => "admins",

        "kick" => "kick",
        "ban" => "ban",
        "unban" => "unban",
        "banlist" => "banlist",
        "mute" => "mute",
        "tmute" => "tmute",
        "unmute" => "unmute",
        "mutelist" => "mutelist",
        "warn" => "warn",
        "unwarn" => "unwarn",
        "unwarns" => "unwarns",
        "status" => "status",
        "setwarns" => "setwarns",
        "tban" => "tban",
        "susermsg" => "susermsg",

        "add" => "add",
        "charge" => "charge",
        "check" => "check",
        "vip" => "vip",
        "nvip" => "nvip",
        "chargevip" => "chargevip",
        "checkvip" => "checkvip",
        "settings" => "settings"
    ];

    if (isset($map[$twoWord])) {
        return $map[$twoWord];
    }

    return $map[$one] ?? $one;
}


/* =========================
   تنفيذ الأوامر
========================= */

function handleCommand($command, $m) {

    global $chatId, $fromId, $messageData;

    $messageData = $m;

    $chatId = $m["chat"]["id"] ?? 0;
    $fromId = $m["from"]["id"] ?? 0;

    $command = botarNormalizeCommand($m);

    /* ---------- تفعيل ---------- */

    if ($command === "add") {

        if (!botarIsDeveloper($fromId) && !botarIsAssistant($fromId)) {
            sendMessage($chatId, "⛔️ التفعيل للمطور أو مساعد المطور فقط.");
            return;
        }

        $g = botarGroup($chatId);

        $g["active"] = true;

        if (($g["expire"] ?? 0) < time()) {
            $g["expire"] = time() + (7 * 86400);
        }

        botarUpdateGroup($chatId, $g);

        sendMessage(
            $chatId,
            "✅ <b>تم تفعيل Botar</b>\n\n"
            . "🛡 يجب رفع البوت مشرفًا ومنحه صلاحيات الحذف والحظر والكتم."
        );

        if (SUDO_ID) {
            sendMessage(
                SUDO_ID,
                "🔔 <b>تفعيل مجموعة جديدة</b>\n\n"
                . "📌 المجموعة: " . htmlspecialchars($g["title"]) . "\n"
                . "🆔 الأيدي: <code>" . $chatId . "</code>\n"
                . "👤 بواسطة: <code>" . $fromId . "</code>"
            );
        }

        return;
    }


    /* ---------- شحن ---------- */

    if ($command === "charge") {

        if (!botarIsDeveloper($fromId) && !botarIsAssistant($fromId)) {
            sendMessage($chatId, "⛔️ الشحن للمطور أو مساعد المطور فقط.");
            return;
        }

        $parts = preg_split('/\s+/u', trim($m["text"] ?? ""));
        $days = isset($parts[1]) && is_numeric($parts[1])
            ? (int)$parts[1]
            : 7;

        if ($days <= 0) {
            $days = 7;
        }

        $expire = botarAddDays($chatId, $days, false);

        sendMessage(
            $chatId,
            "✅ تم شحن المجموعة <b>{$days}</b> يوم."
        );

        if (SUDO_ID) {
            sendMessage(
                SUDO_ID,
                "💳 <b>شحن مجموعة</b>\n\n"
                . "📌 المجموعة: " . htmlspecialchars($m["chat"]["title"] ?? "") . "\n"
                . "🆔 <code>{$chatId}</code>\n"
                . "📅 الأيام المضافة: <b>{$days}</b>\n"
                . "👤 المنفذ: <code>{$fromId}</code>"
            );
        }

        return;
    }


    /* ---------- فحص ---------- */

    if ($command === "check" || $command === "checkvip") {

        if (!botarIsManager($chatId, $fromId)) {
            sendMessage($chatId, "⛔️ ليس لديك صلاحية.");
            return;
        }

        $g = botarGroup($chatId, false);

        if (!$g) {
            sendMessage($chatId, "❌ المجموعة غير مسجلة.");
            return;
        }

        $remaining = max(0, ($g["expire"] ?? 0) - time());
        $days = ceil($remaining / 86400);

        sendMessage(
            $chatId,
            "📊 <b>حالة اشتراك المجموعة</b>\n\n"
            . "📌 الاسم: " . htmlspecialchars($g["title"]) . "\n"
            . "🆔 الأيدي: <code>{$chatId}</code>\n"
            . "📅 الأيام المتبقية: <b>{$days}</b>\n"
            . "💎 النوع: " . (($g["vip"] ?? false) ? "VIP" : "Free")
        );

        return;
    }


    /* ---------- VIP ---------- */

    if ($command === "vip") {

        if (!botarIsDeveloper($fromId)) {
            sendMessage($chatId, "⛔️ الترقية للمطور فقط.");
            return;
        }

        $g = botarGroup($chatId);
        $g["vip"] = true;

        botarUpdateGroup($chatId, $g);

        sendMessage($chatId, "💎 تم ترقية المجموعة إلى VIP.");

        return;
    }


    /* ---------- NVIP ---------- */

    if ($command === "nvip") {

        if (!botarIsDeveloper($fromId)) {
            sendMessage($chatId, "⛔️ هذا الأمر للمطور فقط.");
            return;
        }

        $g = botarGroup($chatId);
        $g["vip"] = false;

        botarUpdateGroup($chatId, $g);

        sendMessage($chatId, "📣 تم إرجاع المجموعة إلى Free.");

        return;
    }


    /* ---------- شحن VIP ---------- */

    if ($command === "chargevip") {

        if (!botarIsDeveloper($fromId)) {
            sendMessage($chatId, "⛔️ هذا الأمر للمطور فقط.");
            return;
        }

        $parts = preg_split('/\s+/u', trim($m["text"] ?? ""));
        $days = isset($parts[2]) && is_numeric($parts[2])
            ? (int)$parts[2]
            : 30;

        botarAddDays($chatId, $days, true);

        sendMessage(
            $chatId,
            "💎 تم شحن VIP لمدة <b>{$days}</b> يوم."
        );

        return;
    }


    /* ---------- رفع مدير ---------- */

    if ($command === "setmanager") {

        if (!botarRequireManager($m)) {
            return;
        }

        $target = botarTarget($m);

        if (!$target) {
            sendMessage($chatId, "⚠️ رد على العضو أو اكتب الآيدي/المعرف.");
            return;
        }

        $g = botarGroup($chatId);

        $exists = false;

        foreach ($g["managers"] as $x) {
            if ((string)($x["id"] ?? $x) === (string)$target["id"]) {
                $exists = true;
            }
        }

        if (!$exists) {
            $g["managers"][] = [
                "id" => $target["id"],
                "name" => $target["name"],
                "username" => $target["username"]
            ];
        }

        botarUpdateGroup($chatId, $g);

        tg("promoteChatMember", [
            "chat_id" => $chatId,
            "user_id" => $target["id"],
            "can_manage_chat" => true,
            "can_delete_messages" => true,
            "can_restrict_members" => true,
            "can_invite_users" => true,
            "can_pin_messages" => true
        ]);

        sendMessage(
            $chatId,
            "👑 تم رفع <b>" . htmlspecialchars($target["name"]) . "</b> مديرًا."
        );

        return;
    }


    /* ---------- إزالة مدير ---------- */

    if ($command === "remmanger") {

        if (!botarRequireManager($m)) {
            return;
        }

        $target = botarTarget($m);

        if (!$target) {
            sendMessage($chatId, "⚠️ رد على العضو أو اكتب الآيدي/المعرف.");
            return;
        }

        $g = botarGroup($chatId);

        $new = [];

        foreach ($g["managers"] as $x) {
            if ((string)($x["id"] ?? $x) !== (string)$target["id"]) {
                $new[] = $x;
            }
        }

        $g["managers"] = $new;

        botarUpdateGroup($chatId, $g);

        tg("promoteChatMember", [
            "chat_id" => $chatId,
            "user_id" => $target["id"],
            "can_manage_chat" => false,
            "can_delete_messages" => false,
            "can_restrict_members" => false,
            "can_invite_users" => false,
            "can_pin_messages" => false
        ]);

        sendMessage($chatId, "✅ تم إزالة المدير.");

        return;
    }


    /* ---------- المدراء ---------- */

    if ($command === "mangers") {

        if (!botarIsAdmin($chatId, $fromId)) {
            sendMessage($chatId, "⛔️ ليس لديك صلاحية.");
            return;
        }

        $g = botarGroup($chatId, false);

        $text = "👑 <b>مدراء المجموعة</b>\n\n";

        if (!$g || empty($g["managers"])) {
            $text .= "لا يوجد مدراء مضافون.";
        } else {
            foreach ($g["managers"] as $x) {
                $text .= "• " . htmlspecialchars($x["name"] ?? $x["id"]) .
                    " — <code>" . $x["id"] . "</code>\n";
            }
        }

        sendMessage($chatId, $text);

        return;
    }


    /* ---------- رفع مشرف ---------- */

    if ($command === "setadmin") {

        if (!botarRequireManager($m)) {
            return;
        }

        $target = botarTarget($m);

        if (!$target) {
            sendMessage($chatId, "⚠️ رد على العضو أو اكتب الآيدي/المعرف.");
            return;
        }

        tg("promoteChatMember", [
            "chat_id" => $chatId,
            "user_id" => $target["id"],
            "can_delete_messages" => true,
            "can_restrict_members" => true,
            "can_invite_users" => true,
            "can_pin_messages" => true
        ]);

        $g = botarGroup($chatId);

        $g["admins"][] = [
            "id" => $target["id"],
            "name" => $target["name"],
            "username" => $target["username"]
        ];

        botarUpdateGroup($chatId, $g);

        sendMessage(
            $chatId,
            "🛡 تم رفع <b>" . htmlspecialchars($target["name"]) . "</b> مشرفًا."
        );

        return;
    }


    /* ---------- إزالة مشرف ---------- */

    if ($command === "remadmin") {

        if (!botarRequireManager($m)) {
            return;
        }

        $target = botarTarget($m);

        if (!$target) {
            sendMessage($chatId, "⚠️ رد على العضو أو اكتب الآيدي.");
            return;
        }

        tg("promoteChatMember", [
            "chat_id" => $chatId,
            "user_id" => $target["id"],
            "can_delete_messages" => false,
            "can_restrict_members" => false,
            "can_invite_users" => false,
            "can_pin_messages" => false
        ]);

        $g = botarGroup($chatId);

        $g["admins"] = array_values(array_filter(
            $g["admins"],
            function ($x) use ($target) {
                return (string)($x["id"] ?? $x) !== (string)$target["id"];
            }
        ));

        botarUpdateGroup($chatId, $g);

        sendMessage($chatId, "✅ تم إزالة المشرف.");

        return;
    }


    /* ---------- المشرفين ---------- */

    if ($command === "admins") {

        if (!botarIsAdmin($chatId, $fromId)) {
            sendMessage($chatId, "⛔️ ليس لديك صلاحية.");
            return;
        }

        $r = tg("getChatAdministrators", [
            "chat_id" => $chatId
        ]);

        $admins = $r["result"] ?? [];

        $text = "🛡 <b>مشرفو المجموعة</b>\n\n";

        foreach ($admins as $a) {
            $u = $a["user"] ?? [];
            $text .= "• " . htmlspecialchars(userName($u))
                . " — <code>" . ($u["id"] ?? "") . "</code>\n";
        }

        sendMessage($chatId, $text);

        return;
    }


    /* ---------- طرد ---------- */

    if ($command === "kick") {

        if (!botarRequireAdmin($m)) {
            return;
        }

        $target = botarTarget($m);

        if (!$target) {
            sendMessage($chatId, "⚠️ رد على رسالة العضو أو اكتب معرفه/آيديه.");
            return;
        }

        $r = tg("banChatMember", [
            "chat_id" => $chatId,
            "user_id" => $target["id"]
        ]);

        if (($r["ok"] ?? false)) {

            tg("unbanChatMember", [
                "chat_id" => $chatId,
                "user_id" => $target["id"],
                "only_if_banned" => true
            ]);

            sendMessage($chatId, "✅ تم طرد العضو.");
        } else {
            sendMessage($chatId, "❌ فشل الطرد. تأكد من صلاحيات البوت.");
        }

        return;
    }


    /* ---------- حظر ---------- */

    if ($command === "ban") {

        if (!botarRequireAdmin($m)) {
            return;
        }

        $target = botarTarget($m);

        if (!$target) {
            sendMessage($chatId, "⚠️ رد على العضو أو اكتب معرفه/آيديه.");
            return;
        }

        $r = tg("banChatMember", [
            "chat_id" => $chatId,
            "user_id" => $target["id"]
        ]);

        if (($r["ok"] ?? false)) {

            $g = botarGroup($chatId);

            $g["banned"][(string)$target["id"]] = [
                "id" => $target["id"],
                "name" => $target["name"],
                "username" => $target["username"],
                "time" => time()
            ];

            botarUpdateGroup($chatId, $g);

            sendMessage($chatId, "🚫 تم حظر العضو.");

        } else {
            sendMessage($chatId, "❌ فشل الحظر.");
        }

        return;
    }


    /* ---------- إلغاء الحظر ---------- */

    if ($command === "unban") {

        if (!botarRequireAdmin($m)) {
            return;
        }

        $target = botarTarget($m);

        if (!$target) {
            sendMessage($chatId, "⚠️ رد على العضو أو اكتب الآيدي.");
            return;
        }

        $r = tg("unbanChatMember", [
            "chat_id" => $chatId,
            "user_id" => $target["id"],
            "only_if_banned" => true
        ]);

        if (($r["ok"] ?? false)) {

            $g = botarGroup($chatId);
            unset($g["banned"][(string)$target["id"]]);
            botarUpdateGroup($chatId, $g);

            sendMessage($chatId, "✅ تم إلغاء حظر العضو.");

        } else {
            sendMessage($chatId, "❌ فشل إلغاء الحظر.");
        }

        return;
    }


    /* ---------- قائمة المحظورين ---------- */

    if ($command === "banlist") {

        if (!botarRequireAdmin($m)) {
            return;
        }

        $g = botarGroup($chatId, false);

        $text = "🚫 <b>المحظورون</b>\n\n";

        if (!$g || empty($g["banned"])) {
            $text .= "القائمة فارغة.";
        } else {
            foreach ($g["banned"] as $x) {
                $text .= "• " . htmlspecialchars($x["name"]) .
                    " — <code>" . $x["id"] . "</code>\n";
            }
        }

        sendMessage($chatId, $text);

        return;
    }


    /* ---------- كتم ---------- */

    if ($command === "mute" || $command === "tmute") {

        if (!botarRequireAdmin($m)) {
            return;
        }

        if ($command === "tmute" && !botarGroup($chatId)["vip"]) {
            sendMessage($chatId, "💎 هذا الأمر متاح للمجموعات VIP فقط.");
            return;
        }

        $target = botarTarget($m);

        if (!$target) {
            sendMessage($chatId, "⚠️ رد على العضو أو اكتب الآيدي.");
            return;
        }

        $until = 0;

        if ($command === "tmute") {
            $parts = preg_split('/\s+/u', trim($m["text"] ?? ""));
            $minutes = isset($parts[2]) && is_numeric($parts[2])
                ? (int)$parts[2]
                : 10;

            $until = time() + ($minutes * 60);
        }

        $r = restrictUser(
            $chatId,
            $target["id"],
            $until,
            false
        );

        if (($r["ok"] ?? false)) {

            $g = botarGroup($chatId);

            $g["muted"][(string)$target["id"]] = [
                "id" => $target["id"],
                "name" => $target["name"],
                "until" => $until
            ];

            botarUpdateGroup($chatId, $g);

            sendMessage(
                $chatId,
                $command === "tmute"
                    ? "🔇 تم كتم العضو مؤقتًا."
                    : "🔇 تم كتم العضو."
            );

        } else {
            sendMessage($chatId, "❌ فشل الكتم.");
        }

        return;
    }


    /* ---------- إلغاء الكتم ---------- */

    if ($command === "unmute") {

        if (!botarRequireAdmin($m)) {
            return;
        }

        $target = botarTarget($m);

        if (!$target) {
            sendMessage($chatId, "⚠️ رد على العضو.");
            return;
        }

        $r = restrictUser(
            $chatId,
            $target["id"],
            0,
            true
        );

        if (($r["ok"] ?? false)) {

            $g = botarGroup($chatId);

            unset($g["muted"][(string)$target["id"]]);

            botarUpdateGroup($chatId, $g);

            sendMessage($chatId, "🔊 تم إلغاء كتم العضو.");

        } else {
            sendMessage($chatId, "❌ فشل إلغاء الكتم.");
        }

        return;
    }


    /* ---------- قائمة المكتومين ---------- */

    if ($command === "mutelist") {

        if (!botarRequireAdmin($m)) {
            return;
        }

        $g = botarGroup($chatId, false);

        $text = "🔇 <b>المكتومون</b>\n\n";

        if (!$g || empty($g["muted"])) {
            $text .= "القائمة فارغة.";
        } else {
            foreach ($g["muted"] as $x) {
                $text .= "• " . htmlspecialchars($x["name"])
                    . " — <code>" . $x["id"] . "</code>\n";
            }
        }

        sendMessage($chatId, $text);

        return;
    }


    /* ---------- تحذير ---------- */

    if ($command === "warn") {

        if (!botarRequireAdmin($m)) {
            return;
        }

        $target = botarTarget($m);

        if (!$target) {
            sendMessage($chatId, "⚠️ رد على العضو.");
            return;
        }

        $g = botarGroup($chatId);

        $id = (string)$target["id"];

        $g["warns"][$id] = ($g["warns"][$id] ?? 0) + 1;

        $count = $g["warns"][$id];
        $limit = (int)($g["warn_limit"] ?? 3);

        botarUpdateGroup($chatId, $g);

        if ($count >= $limit) {

            $action = $g["warn_action"] ?? "kick";

            if ($action === "ban") {

                tg("banChatMember", [
                    "chat_id" => $chatId,
                    "user_id" => $target["id"]
                ]);

                $msg = "🚫 وصل العضو للحد الأقصى وتم حظره.";

            } elseif ($action === "mute") {

                restrictUser(
                    $chatId,
                    $target["id"],
                    0,
                    false
                );

                $msg = "🔇 وصل العضو للحد الأقصى وتم كتمه.";

            } else {

                tg("banChatMember", [
                    "chat_id" => $chatId,
                    "user_id" => $target["id"]
                ]);

                tg("unbanChatMember", [
                    "chat_id" => $chatId,
                    "user_id" => $target["id"],
                    "only_if_banned" => true
                ]);

                $msg = "⛔️ وصل العضو للحد الأقصى وتم طرده.";
            }

            $g["warns"][$id] = 0;
            botarUpdateGroup($chatId, $g);

            sendMessage($chatId, $msg);

        } else {

            sendMessage(
                $chatId,
                "⚠️ تم تحذير العضو.\n\n"
                . "التحذيرات: <b>{$count}/{$limit}</b>"
            );
        }

        return;
    }


    /* ---------- إزالة تحذير ---------- */

    if ($command === "unwarn") {

        if (!botarRequireAdmin($m)) {
            return;
        }

        $target = botarTarget($m);

        if (!$target) {
            sendMessage($chatId, "⚠️ رد على العضو.");
            return;
        }

        $g = botarGroup($chatId);

        $id = (string)$target["id"];

        $g["warns"][$id] = max(
            0,
            ($g["warns"][$id] ?? 0) - 1
        );

        botarUpdateGroup($chatId, $g);

        sendMessage($chatId, "✅ تم إزالة تحذير.");

        return;
    }


    /* ---------- إزالة كل التحذيرات ---------- */

    if ($command === "unwarns") {

        if (!botarRequireAdmin($m)) {
            return;
        }

        $target = botarTarget($m);

        if (!$target) {
            sendMessage($chatId, "⚠️ رد على العضو.");
            return;
        }

        $g = botarGroup($chatId);

        unset($g["warns"][(string)$target["id"]]);

        botarUpdateGroup($chatId, $g);

        sendMessage($chatId, "✅ تم حذف جميع تحذيرات العضو.");

        return;
    }


    /* ---------- الحالة ---------- */

    if ($command === "status") {

        if (!botarIsAdmin($chatId, $fromId)) {
            sendMessage($chatId, "⛔️ ليس لديك صلاحية.");
            return;
        }

        $target = botarTarget($m);

        if (!$target) {
            sendMessage($chatId, "⚠️ رد على العضو.");
            return;
        }

        $g = botarGroup($chatId, false);

        $warns = $g["warns"][(string)$target["id"]] ?? 0;

        sendMessage(
            $chatId,
            "👤 <b>معلومات العضو</b>\n\n"
            . "الاسم: " . htmlspecialchars($target["name"]) . "\n"
            . "🆔 <code>" . $target["id"] . "</code>\n"
            . "⚠️ التحذيرات: <b>{$warns}/" . ($g["warn_limit"] ?? 3) . "</b>"
        );

        return;
    }


    /* ---------- تعيين التحذيرات ---------- */

    if ($command === "setwarns") {

        if (!botarRequireManager($m)) {
            return;
        }

        $parts = preg_split('/\s+/u', trim($m["text"] ?? ""));

        $limit = isset($parts[2]) && is_numeric($parts[2])
            ? (int)$parts[2]
            : 3;

        if ($limit < 1) {
            $limit = 3;
        }

        $g = botarGroup($chatId);
        $g["warn_limit"] = $limit;

        botarUpdateGroup($chatId, $g);

        sendMessage(
            $chatId,
            "⚙️ تم تحديد الحد الأقصى للتحذيرات إلى <b>{$limit}</b>."
        );

        return;
    }


    /* ---------- حظر مؤقت ---------- */

    if ($command === "tban") {

        if (!botarRequireAdmin($m)) {
            return;
        }

        $g = botarGroup($chatId);

        if (!$g["vip"]) {
            sendMessage($chatId, "💎 هذا الأمر متاح للمجموعات VIP فقط.");
            return;
        }

        $target = botarTarget($m);

        if (!$target) {
            sendMessage($chatId, "⚠️ رد على العضو.");
            return;
        }

        $parts = preg_split('/\s+/u', trim($m["text"] ?? ""));

        $minutes = isset($parts[2]) && is_numeric($parts[2])
            ? (int)$parts[2]
            : 10;

        $until = time() + ($minutes * 60);

        $r = tg("banChatMember", [
            "chat_id" => $chatId,
            "user_id" => $target["id"],
            "until_date" => $until
        ]);

        if (($r["ok"] ?? false)) {
            sendMessage(
                $chatId,
                "🚫 تم حظر العضو لمدة <b>{$minutes}</b> دقيقة."
            );
        } else {
            sendMessage($chatId, "❌ فشل الحظر المؤقت.");
        }

        return;
    }


    /* ---------- تحديد الرسائل ---------- */

    if ($command === "susermsg") {

        if (!botarRequireManager($m)) {
            return;
        }

        $g = botarGroup($chatId);

        if (!$g["vip"]) {
            sendMessage($chatId, "💎 هذا الأمر متاح للمجموعات VIP فقط.");
            return;
        }

        $parts = preg_split('/\s+/u', trim($m["text"] ?? ""));

        $limit = isset($parts[2]) && is_numeric($parts[2])
            ? (int)$parts[2]
            : 50;

        $g["message_limit"] = $limit;

        botarUpdateGroup($chatId, $g);

        sendMessage(
            $chatId,
            "✅ تم تحديد الحد اليومي إلى <b>{$limit}</b> رسالة لكل عضو."
        );

        return;
    }


    /* =========================
       الإعدادات
    ========================= */

    if ($command === "settings") {

        if (!botarRequireAdmin($m)) {
            return;
        }

        $keyboard = [
            "inline_keyboard" => [
                [
                    [
                        "text" => "📍 مكان التحكم",
                        "callback_data" => "b_settings_place"
                    ]
                ],
                [
                    [
                        "text" => "⚙️ إعدادات عامة",
                        "callback_data" => "b_settings_general"
                    ]
                ],
                [
                    [
                        "text" => "🔒 إعدادات القفل",
                        "callback_data" => "b_settings_locks"
                    ]
                ],
                [
                    [
                        "text" => "🔔 الإشعارات",
                        "callback_data" => "b_settings_notify"
                    ]
                ]
            ]
        ];

        sendMessage(
            $chatId,
            "⚙️ <b>إعدادات Botar</b>\n\nاختر القسم:",
            $keyboard
        );

        return;
    }


    /* ---------- غير معروف ---------- */

    if ($command !== "") {

        sendMessage(
            $chatId,
            "❓ الأمر غير معروف.\n\n"
            . "استخدم <code>اعدادات</code> للإعدادات."
        );
    }
}


/* =========================
   الأقفال
========================= */

function moderateLocks($m) {

    $chatId = $m["chat"]["id"] ?? 0;
    $fromId = $m["from"]["id"] ?? 0;

    if (!$chatId || !$fromId) {
        return;
    }

    if (botarIsAdmin($chatId, $fromId)) {
        return;
    }

    $g = botarGroup($chatId, false);

    if (!$g) {
        return;
    }

    $locks = $g["locks"] ?? [];

    if (empty($locks)) {
        return;
    }

    $type = "";

    if (isset($m["photo"])) {
        $type = "photos";
    } elseif (isset($m["video"])) {
        $type = "video";
    } elseif (isset($m["voice"])) {
        $type = "voice";
    } elseif (isset($m["audio"])) {
        $type = "audio";
    } elseif (isset($m["sticker"])) {
        $type = "stickers";
    } elseif (isset($m["animation"])) {
        $type = "gif";
    } elseif (isset($m["video_note"])) {
        $type = "video_notes";
    } elseif (isset($m["contact"])) {
        $type = "contacts";
    } elseif (isset($m["location"])) {
        $type = "locations";
    } elseif (isset($m["forward_origin"])) {
        $type = "forward";
    }

    if ($type === "" && isset($m["text"])) {

        $text = $m["text"];

        if (preg_match('/https?:\/\/|www\./iu', $text)) {
            $type = "links";
        } elseif (preg_match('/@\w+/u', $text)) {
            $type = "tags";
        } elseif (preg_match('/#\S+/u', $text)) {
            $type = "hashtags";
        }
    }

    if ($type === "" || !isset($locks[$type])) {
        return;
    }

    if (!$locks[$type]) {
        return;
    }

    $messageId = $m["message_id"] ?? 0;

    if ($messageId) {
        tg("deleteMessage", [
            "chat_id" => $chatId,
            "message_id" => $messageId
        ]);
    }
}


/* =========================
   Callback
========================= */

function handleCallback($cq, $chat, $mid, $uid, $data) {

    $id = $cq["id"] ?? "";

    if (!botarIsAdmin($chat, $uid) && !botarIsDeveloper($uid)) {
        answerCb($id, "⛔️ ليس لديك صلاحية.");
        return;
    }

    answerCb($id);

    $g = botarGroup($chat);

    /* ---------- مكان التحكم ---------- */

    if ($data === "b_settings_place") {

        $keyboard = [
            "inline_keyboard" => [
                [
                    [
                        "text" => "📍 في المجموعة",
                        "callback_data" => "b_place_group"
                    ]
                ],
                [
                    [
                        "text" => "📩 في الخاص",
                        "callback_data" => "b_place_private"
                    ]
                ],
                [
                    [
                        "text" => "🔙 رجوع",
                        "callback_data" => "b_settings"
                    ]
                ]
            ]
        ];

        editMessage(
            $chat,
            $mid,
            "📍 <b>مكان التحكم</b>\n\nاختر مكان ظهور إعدادات المجموعة:",
            $keyboard
        );

        return;
    }


    if ($data === "b_place_group") {

        $g["control_place"] = "group";
        botarUpdateGroup($chat, $g);

        editMessage(
            $chat,
            $mid,
            "✅ تم اختيار التحكم من المجموعة."
        );

        return;
    }


    if ($data === "b_place_private") {

        $g["control_place"] = "private";
        botarUpdateGroup($chat, $g);

        editMessage(
            $chat,
            $mid,
            "✅ تم اختيار التحكم من الخاص."
        );

        return;
    }


    /* ---------- الإعدادات العامة ---------- */

    if ($data === "b_settings_general") {

        $welcome = !empty($g["welcome"]);
        $deleteWelcome = !empty($g["welcome_delete"]);
        $rules = !empty($g["rules"]);

        $keyboard = [
            "inline_keyboard" => [
                [
                    [
                        "text" => ($welcome ? "✅" : "☑️") . " رسالة الترحيب",
                        "callback_data" => "b_toggle_welcome"
                    ]
                ],
                [
                    [
                        "text" => ($deleteWelcome ? "✅" : "☑️") . " حذف آخر ترحيب",
                        "callback_data" => "b_toggle_welcome_delete"
                    ]
                ],
                [
                    [
                        "text" => ($rules ? "✅" : "☑️") . " القوانين",
                        "callback_data" => "b_toggle_rules"
                    ]
                ],
                [
                    [
                        "text" => "⚠️ عدد التحذيرات",
                        "callback_data" => "b_warn_limit"
                    ]
                ],
                [
                    [
                        "text" => "🔙 رجوع",
                        "callback_data" => "b_settings"
                    ]
                ]
            ]
        ];

        editMessage(
            $chat,
            $mid,
            "⚙️ <b>الإعدادات العامة</b>",
            $keyboard
        );

        return;
    }


    if ($data === "b_toggle_welcome") {

        $g["welcome"] = empty($g["welcome"]);
        botarUpdateGroup($chat, $g);

        handleCallback(
            [
                "id" => $id
            ],
            $chat,
            $mid,
            $uid,
            "b_settings_general"
        );

        return;
    }


    if ($data === "b_toggle_welcome_delete") {

        $g["welcome_delete"] = empty($g["welcome_delete"]);
        botarUpdateGroup($chat, $g);

        handleCallback(
            [
                "id" => $id
            ],
            $chat,
            $mid,
            $uid,
            "b_settings_general"
        );

        return;
    }


    if ($data === "b_toggle_rules") {

        $g["rules"] = empty($g["rules"]) ? "لم يتم تعيين القوانين." : "";
        botarUpdateGroup($chat, $g);

        handleCallback(
            [
                "id" => $id
            ],
            $chat,
            $mid,
            $uid,
            "b_settings_general"
        );

        return;
    }


    /* ---------- إعدادات الأقفال ---------- */

    if ($data === "b_settings_locks") {

        $locks = [
            "photos" => "الصور",
            "video" => "الفيديو",
            "voice" => "التسجيلات",
            "audio" => "الصوتيات",
            "stickers" => "الملصقات",
            "gif" => "الصور المتحركة",
            "video_notes" => "تسجيلات الفيديو",
            "links" => "الروابط",
            "forward" => "التوجيه",
            "contacts" => "جهات الاتصال",
            "locations" => "المواقع",
            "tags" => "التاق",
            "hashtags" => "الهاشتاق"
        ];

        $rows = [];

        foreach ($locks as $key => $name) {

            $on = !empty($g["locks"][$key]);

            $rows[] = [
                [
                    "text" => ($on ? "🗑" : "☑️") . " " . $name,
                    "callback_data" => "b_lock_" . $key
                ]
            ];
        }

        $rows[] = [
            [
                "text" => "🔙 رجوع",
                "callback_data" => "b_settings"
            ]
        ];

        editMessage(
            $chat,
            $mid,
            "🔒 <b>إعدادات القفل</b>\n\n"
            . "🗑 = مفعل بالحذف\n"
            . "☑️ = معطل",
            [
                "inline_keyboard" => $rows
            ]
        );

        return;
    }


    /* ---------- تبديل الأقفال ---------- */

    if (strpos($data, "b_lock_") === 0) {

        $key = substr($data, 7);

        if (!isset($g["locks"])) {
            $g["locks"] = [];
        }

        $g["locks"][$key] = empty($g["locks"][$key]);

        botarUpdateGroup($chat, $g);

        handleCallback(
            [
                "id" => $id
            ],
            $chat,
            $mid,
            $uid,
            "b_settings_locks"
        );

        return;
    }


    /* ---------- إعدادات الإشعارات ---------- */

    if ($data === "b_settings_notify") {

        editMessage(
            $chat,
            $mid,
            "🔔 <b>إعدادات الإشعارات</b>\n\n"
            . "هذه الصفحة مخصصة لربط المجموعة بقناة الإشعارات."
        );

        return;
    }


    /* ---------- العودة ---------- */

    if ($data === "b_settings") {

        $keyboard = [
            "inline_keyboard" => [
                [
                    [
                        "text" => "📍 مكان التحكم",
                        "callback_data" => "b_settings_place"
                    ]
                ],
                [
                    [
                        "text" => "⚙️ إعدادات عامة",
                        "callback_data" => "b_settings_general"
                    ]
                ],
                [
                    [
                        "text" => "🔒 إعدادات القفل",
                        "callback_data" => "b_settings_locks"
                    ]
                ],
                [
                    [
                        "text" => "🔔 الإشعارات",
                        "callback_data" => "b_settings_notify"
                    ]
                ]
            ]
        ];

        editMessage(
            $chat,
            $mid,
            "⚙️ <b>إعدادات Botar</b>\n\nاختر القسم:",
            $keyboard
        );

        return;
    }
}


/* =========================
   الأوامر القديمة
   للتوافق مع أي ملفات أخرى
========================= */

function command_ping() {
    global $chatId;
    sendMessage($chatId, "🏓 Pong!");
}

function command_start() {
    global $chatId;

    sendMessage(
        $chatId,
        "🤖 <b>مرحبًا بك في Botar</b>\n\n"
        . "🛡 بوت حماية وإدارة المجموعات.\n\n"
        . "استخدم الأوامر العربية أو الإنجليزية."
    );
}

function command_kick() {
    global $messageData;
    handleCommand("kick", $messageData);
}
