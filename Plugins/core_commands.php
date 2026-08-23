<?php

/*
 * Botar Core Commands
 * متوافق مع index.php و util.php الحاليين
 */

/* =========================
   بيانات المجموعة
========================= */

function ensureChat($m) {
    $data = readJson("groups", []);

    $chatId = (string)$m["chat"]["id"];

    if (!isset($data[$chatId])) {
        $data[$chatId] = [
            "id" => $m["chat"]["id"],
            "title" => $m["chat"]["title"] ?? "بدون اسم",
            "welcome" => true,
            "rules" => "",
            "warns" => [],
            "locks" => [],
            "managers" => [],
            "admins" => [],
            "settings" => []
        ];

        writeJson("groups", $data);
    }
}

/* =========================
   صلاحيات
========================= */

function userIsAdmin($chatId, $userId) {
    return canManage($chatId, $userId) || isSudo($userId);
}

function requireAdmin($m) {
    global $chatId, $fromId;

    if (!userIsAdmin($chatId, $fromId)) {
        sendMessage($chatId, "⛔️ هذا الأمر للمشرفين فقط.");
        return false;
    }

    return true;
}

/* =========================
   الحماية
========================= */

function moderateLocks($m) {
    /*
     * نظام القفل الأساسي.
     * سيتم توسيعه لاحقًا لإضافة:
     * الصور، الفيديو، الروابط، الملصقات، الصوتيات...
     */
    return;
}

/* =========================
   الأوامر
========================= */

function handleCommand($command, $m) {
    global $chatId, $fromId, $messageData;

    $messageData = $m;

    switch ($command) {

        /* ---------- أساسي ---------- */

        case "ping":
            sendMessage($chatId, "🏓 Pong!");
            return;

        case "start":
            sendMessage(
                $chatId,
                "🤖 <b>أهلاً بك في بوت Botar</b>\n\n"
                . "🛡 بوت حماية وإدارة للمجموعات\n\n"
                . "استخدم <code>/commands</code> لعرض الأوامر."
            );
            return;

        case "commands":
            sendMessage(
                $chatId,
                "📚 <b>أوامر Botar</b>\n\n"
                . "🛡 الحماية:\n"
                . "طرد - حظر - الغاء حظر - كتم - الغاء كتم\n"
                . "تحذير - الغاء التحذير - الحالة\n\n"
                . "👮 الإدارة:\n"
                . "رفع مدير - ازالة مدير - المدراء\n"
                . "رفع مشرف - ازالة مشرف - المشرفين\n\n"
                . "⚙️ الإعدادات:\n"
                . "اعدادات"
            );
            return;

        /* ---------- طرد ---------- */

        case "kick":

            if (!requireAdmin($m)) return;

            $target = extractTarget($m);

            if (!$target) {
                sendMessage(
                    $chatId,
                    "⚠️ يجب أن ترد على رسالة العضو أو تكتب معرفه/ايديه."
                );
                return;
            }

            $result = tg("banChatMember", [
                "chat_id" => $chatId,
                "user_id" => $target["id"]
            ]);

            if (($result["ok"] ?? false)) {

                tg("unbanChatMember", [
                    "chat_id" => $chatId,
                    "user_id" => $target["id"],
                    "only_if_banned" => true
                ]);

                sendMessage(
                    $chatId,
                    "✅ تم طرد العضو."
                );

            } else {
                sendMessage(
                    $chatId,
                    "❌ لم أستطع طرد العضو.\nتأكد أن البوت مشرف."
                );
            }

            return;

        /* ---------- حظر ---------- */

        case "ban":

            if (!requireAdmin($m)) return;

            $target = extractTarget($m);

            if (!$target) {
                sendMessage(
                    $chatId,
                    "⚠️ يجب أن ترد على رسالة العضو أو تكتب معرفه/ايديه."
                );
                return;
            }

            $result = tg("banChatMember", [
                "chat_id" => $chatId,
                "user_id" => $target["id"]
            ]);

            if (($result["ok"] ?? false)) {
                sendMessage($chatId, "🚫 تم حظر العضو.");
            } else {
                sendMessage(
                    $chatId,
                    "❌ فشل الحظر. تأكد من صلاحيات البوت."
                );
            }

            return;

        /* ---------- إلغاء الحظر ---------- */

        case "unban":

            if (!requireAdmin($m)) return;

            $target = extractTarget($m);

            if (!$target) {
                sendMessage(
                    $chatId,
                    "⚠️ يجب أن ترد على رسالة العضو أو تكتب ايديه."
                );
                return;
            }

            $result = tg("unbanChatMember", [
                "chat_id" => $chatId,
                "user_id" => $target["id"],
                "only_if_banned" => true
            ]);

            if (($result["ok"] ?? false)) {
                sendMessage($chatId, "✅ تم إلغاء حظر العضو.");
            } else {
                sendMessage($chatId, "❌ لم يتم إلغاء الحظر.");
            }

            return;

        /* ---------- كتم ---------- */

        case "mute":

            if (!requireAdmin($m)) return;

            $target = extractTarget($m);

            if (!$target) {
                sendMessage(
                    $chatId,
                    "⚠️ يجب أن ترد على رسالة العضو أو تكتب معرفه/ايديه."
                );
                return;
            }

            $result = restrictUser(
                $chatId,
                $target["id"],
                0,
                false
            );

            if (($result["ok"] ?? false)) {
                sendMessage($chatId, "🔇 تم كتم العضو.");
            } else {
                sendMessage(
                    $chatId,
                    "❌ فشل الكتم. تأكد أن البوت مشرف."
                );
            }

            return;

        /* ---------- إلغاء الكتم ---------- */

        case "unmute":

            if (!requireAdmin($m)) return;

            $target = extractTarget($m);

            if (!$target) {
                sendMessage(
                    $chatId,
                    "⚠️ يجب أن ترد على رسالة العضو."
                );
                return;
            }

            $result = restrictUser(
                $chatId,
                $target["id"],
                0,
                true
            );

            if (($result["ok"] ?? false)) {
                sendMessage($chatId, "🔊 تم إلغاء كتم العضو.");
            } else {
                sendMessage($chatId, "❌ فشل إلغاء الكتم.");
            }

            return;

        /* ---------- إعدادات ---------- */

        case "settings":

            if (!requireAdmin($m)) return;

            $keyboard = [
                "inline_keyboard" => [
                    [
                        [
                            "text" => "⚙️ إعدادات عامة",
                            "callback_data" => "settings_general"
                        ]
                    ],
                    [
                        [
                            "text" => "🔒 إعدادات القفل",
                            "callback_data" => "settings_locks"
                        ]
                    ],
                    [
                        [
                            "text" => "🔔 الإشعارات",
                            "callback_data" => "settings_notify"
                        ]
                    ]
                ]
            ];

            sendMessage(
                $chatId,
                "⚙️ <b>إعدادات المجموعة</b>\n\nاختر القسم الذي تريد التحكم به:",
                $keyboard
            );

            return;

        /* ---------- التفعيل ---------- */

        case "add":

            if (!isSudo($fromId)) {
                sendMessage(
                    $chatId,
                    "⛔️ التفعيل متاح للمطور فقط."
                );
                return;
            }

            sendMessage(
                $chatId,
                "✅ تم تفعيل البوت في المجموعة."
            );

            return;

        default:

            sendMessage(
                $chatId,
                "❓ الأمر غير معروف.\nاستخدم /commands لعرض الأوامر."
            );

            return;
    }
}

/* =========================
   Callback
========================= */

function handleCallback($cq, $chat, $mid, $uid, $data) {

    answerCb($cq["id"] ?? "");

    if (!isSudo($uid) && !userIsAdmin($chat, $uid)) {
        answerCb(
            $cq["id"] ?? "",
            "⛔️ ليس لديك صلاحية."
        );
        return;
    }

    switch ($data) {

        case "settings_general":

            editMessage(
                $chat,
                $mid,
                "⚙️ <b>الإعدادات العامة</b>\n\n"
                . "• الترحيب\n"
                . "• القوانين\n"
                . "• التحذيرات\n"
                . "• طرد البوتات"
            );

            return;

        case "settings_locks":

            editMessage(
                $chat,
                $mid,
                "🔒 <b>إعدادات القفل</b>\n\n"
                . "• الصور\n"
                . "• الفيديو\n"
                . "• الروابط\n"
                . "• الملصقات\n"
                . "• الصوتيات\n"
                . "• التوجيه"
            );

            return;

        case "settings_notify":

            editMessage(
                $chat,
                $mid,
                "🔔 <b>إعدادات الإشعارات</b>\n\n"
                . "نظام الإشعارات جاهز للإضافة."
            );

            return;

        default:
            return;
    }
}

/* =========================
   توافق مع الأسماء القديمة
========================= */

function command_ping() {
    global $chatId;
    sendMessage($chatId, "🏓 Pong!");
}

function command_start() {
    global $chatId;
    sendMessage(
        $chatId,
        "🤖 <b>أهلاً بك في Botar</b>\n\nاستخدم /commands لعرض الأوامر."
    );
}

function command_kick() {
    global $chatId, $messageData;
    handleCommand("kick", $messageData);
}

?>
