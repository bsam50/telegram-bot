<?php

$TOKEN = "8937334713:AAHbK50bbjg7ryrYDM4K_SzrfRq7Yb8FICA";
$botUsername = "ggguuiii_bot";
$sudoID = "8476500086";

date_default_timezone_set("Asia/Riyadh");

define("BOT_TOKEN", $TOKEN);
define("BOT_USERNAME", $botUsername);
define("SUDO_ID", (string)$sudoID);
define("DATA_DIR", __DIR__ . "/data");

if (!is_dir(DATA_DIR)) mkdir(DATA_DIR, 0777, true);

?>
