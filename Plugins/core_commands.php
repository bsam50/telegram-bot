<?php

function command_ping(){
    sendMessage("pong!");
}

function command_start(){
    sendMessage("test 11 test");
}

function command_kick(){
    global $chatId, $messageData;

    if (!isset($messageData["reply_to_message"]["from"]["id"])) {
        sendMessage("⚠️ يجب أن ترد على رسالة العضو الذي تريد طرده.");
        return;
    }

    $userId = $messageData["reply_to_message"]["from"]["id"];

    $result = kickChatMember($chatId, $userId);

    sendMessage("✅ تم طرد العضو.");
}
