<?php
// ضع بيانات البوت هنا فقط
$TOKEN = "PUT_BOT_TOKEN_HERE";
$botUsername = "PUT_BOT_USERNAME_HERE"; // بدون @
$sudoID = "PUT_DEVELOPER_ID_HERE";

date_default_timezone_set("Asia/Riyadh");

define("BOT_TOKEN", $TOKEN);
define("BOT_USERNAME", $botUsername);
define("SUDO_ID", (string)$sudoID);
define("DATA_DIR", __DIR__ . "/data");

if (!is_dir(DATA_DIR)) mkdir(DATA_DIR, 0777, true);
?>
