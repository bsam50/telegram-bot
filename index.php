<?php
require_once "config.php";
require_once "util.php";

foreach (glob("Plugins/*.php") as $plugin) include_once $plugin;

$raw=file_get_contents("php://input");
if(!$raw) exit("Webhook OK");
$u=json_decode($raw,true);
if(!$u) exit;

if(isset($u["callback_query"])) {
    $cq=$u["callback_query"];
    $m=$cq["message"]??[];
    $chat=$m["chat"]["id"]??0; $mid=$m["message_id"]??0;
    $uid=$cq["from"]["id"]??0; $data=$cq["data"]??"";
    handleCallback($cq,$chat,$mid,$uid,$data);
    exit;
}

$m=$u["message"]??null;
if(!$m) exit;

$chatId=$m["chat"]["id"];
$type=$m["chat"]["type"];
$from=$m["from"]??[];
$fromId=$from["id"]??0;
$text=$m["text"]??"";

if(isGroup($type)) {
    ensureChat($m);
    moderateLocks($m);
}

if($text!=="" && preg_match('/^[\/!#]([^\s@]+)/u',$text,$mm)) {
    $command=commandAliases($mm[1]);
    handleCommand($command,$m);
}
?>
