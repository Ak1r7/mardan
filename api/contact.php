<?php

declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: no-referrer');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header("Content-Security-Policy: default-src 'none'; frame-ancestors 'none'");

const MAX_BODY_BYTES = 24_000;
const RATE_LIMIT = 5;
const RATE_WINDOW_SECONDS = 900;
const MIN_FORM_AGE_MS = 1_200;
const MAX_FORM_AGE_MS = 86_400_000;

// =========================================================
// TELEGRAM — ЗАМЕНИТЕ ТОЛЬКО ЭТИ ДВЕ СТРОКИ
// =========================================================
const TELEGRAM_BOT_TOKEN = '8052006626:AAHZ57u-x950FECGZrygfqaN2r_qbXCnawc';
const TELEGRAM_CHAT_ID = '633116671';

function respond(int $status, array $payload): void
{
    http_response_code($status);
    $json = json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    echo $json === false ? '{"ok":false,"message":"Ошибка сериализации ответа."}' : $json;
    exit;
}

function text_length(string $value): int
{
    if (function_exists('mb_strlen')) {
        return mb_strlen($value, 'UTF-8');
    }
    if (preg_match_all('/./us', $value, $matches) !== false) {
        return count($matches[0]);
    }
    return strlen($value);
}

function clean_text(string $value): string
{
    $value = trim($value);
    return preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $value) ?? '';
}

function request_host(): string
{
    $hostHeader = strtolower((string)($_SERVER['HTTP_HOST'] ?? ''));
    if ($hostHeader === '') {
        return '';
    }
    return (string)(parse_url('http://' . $hostHeader, PHP_URL_HOST) ?: '');
}

function tg_escape(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

/**
 * @return array{ok: bool, error: string}
 */
function send_to_telegram(string $text): array
{
    if (
        TELEGRAM_BOT_TOKEN === '' ||
        TELEGRAM_CHAT_ID === '' ||
        TELEGRAM_BOT_TOKEN === 'ВСТАВЬ_ТОКЕН_БОТА' ||
        TELEGRAM_CHAT_ID === 'ВСТАВЬ_CHAT_ID'
    ) {
        return ['ok' => false, 'error' => 'В contact.php не указан токен бота или chat_id.'];
    }

    $url = 'https://api.telegram.org/bot' . TELEGRAM_BOT_TOKEN . '/sendMessage';
    $postData = http_build_query([
        'chat_id' => TELEGRAM_CHAT_ID,
        'text' => $text,
        'parse_mode' => 'HTML',
        'disable_web_page_preview' => 'true',
    ]);

    $responseBody = false;
    $httpCode = 0;
    $transportError = '';

    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        if ($ch === false) {
            return ['ok' => false, 'error' => 'Не удалось инициализировать cURL.'];
        }

        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $postData,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_TIMEOUT => 12,
            CURLOPT_HTTPHEADER => [
                'Content-Type: application/x-www-form-urlencoded',
                'Accept: application/json',
            ],
        ]);

        $responseBody = curl_exec($ch);
        $httpCode = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $transportError = curl_error($ch);
        curl_close($ch);
    } elseif ((bool)ini_get('allow_url_fopen')) {
        $context = stream_context_create([
            'http' => [
                'method' => 'POST',
                'header' => "Content-Type: application/x-www-form-urlencoded\r\nAccept: application/json\r\n",
                'content' => $postData,
                'timeout' => 12,
                'ignore_errors' => true,
            ],
        ]);

        $responseBody = @file_get_contents($url, false, $context);

        if (isset($http_response_header) && is_array($http_response_header)) {
            foreach ($http_response_header as $headerLine) {
                if (preg_match('/^HTTP\/\S+\s+(\d{3})/', $headerLine, $matches)) {
                    $httpCode = (int)$matches[1];
                    break;
                }
            }
        }

        if ($responseBody === false) {
            $lastError = error_get_last();
            $transportError = (string)($lastError['message'] ?? 'Неизвестная ошибка HTTP.');
        }
    } else {
        return [
            'ok' => false,
            'error' => 'На сервере недоступны и cURL, и allow_url_fopen.',
        ];
    }

    if ($responseBody === false) {
        return [
            'ok' => false,
            'error' => 'Ошибка соединения с Telegram: ' . ($transportError !== '' ? $transportError : 'нет ответа'),
        ];
    }

    $decoded = json_decode((string)$responseBody, true);

    if (!is_array($decoded)) {
        return [
            'ok' => false,
            'error' => 'Telegram вернул некорректный ответ (HTTP ' . $httpCode . ').',
        ];
    }

    if ($httpCode !== 200 || ($decoded['ok'] ?? false) !== true) {
        $description = clean_text((string)($decoded['description'] ?? 'Неизвестная ошибка Telegram'));
        return [
            'ok' => false,
            'error' => $description . ($httpCode > 0 ? ' (HTTP ' . $httpCode . ')' : ''),
        ];
    }

    return ['ok' => true, 'error' => ''];
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Allow: POST');
    respond(405, ['ok' => false, 'message' => 'Метод не поддерживается.']);
}

$contentLength = (int)($_SERVER['CONTENT_LENGTH'] ?? 0);
if ($contentLength > MAX_BODY_BYTES) {
    respond(413, ['ok' => false, 'message' => 'Слишком большой объём данных.']);
}

$origin = (string)($_SERVER['HTTP_ORIGIN'] ?? '');
if ($origin !== '') {
    $originHost = strtolower((string)(parse_url($origin, PHP_URL_HOST) ?: ''));
    $host = request_host();
    if ($host === '' || $originHost === '' || !hash_equals($host, $originHost)) {
        respond(403, ['ok' => false, 'message' => 'Некорректный источник запроса.']);
    }
}

$storageRoot = realpath(__DIR__ . '/../storage');
if ($storageRoot === false) {
    respond(500, ['ok' => false, 'message' => 'Не настроено серверное хранилище заявок.']);
}

$name = clean_text((string)($_POST['name'] ?? ''));
$phone = clean_text((string)($_POST['phone'] ?? ''));
$message = clean_text((string)($_POST['message'] ?? ''));
$formType = clean_text((string)($_POST['formType'] ?? 'contacts'));
$website = clean_text((string)($_POST['website'] ?? ''));
$formStartedAt = filter_var($_POST['form_started_at'] ?? null, FILTER_VALIDATE_INT);
$consent = isset($_POST['consent']);

if ($website !== '') {
    respond(422, ['ok' => false, 'message' => 'Форма распознана как спам.']);
}
if (!in_array($formType, ['contacts', 'modal', 'quiz'], true)) {
    respond(422, ['ok' => false, 'message' => 'Некорректный тип формы.']);
}
if ($formStartedAt === false) {
    respond(422, ['ok' => false, 'message' => 'Обновите страницу и заполните форму повторно.']);
}
$formAge = (int)round(microtime(true) * 1000) - (int)$formStartedAt;
if ($formAge < MIN_FORM_AGE_MS || $formAge > MAX_FORM_AGE_MS) {
    respond(422, ['ok' => false, 'message' => 'Форма отправлена слишком быстро или устарела. Обновите страницу.']);
}
if (text_length($name) < 2 || text_length($name) > 80) {
    respond(422, ['ok' => false, 'message' => 'Укажите корректное имя.']);
}
$phoneDigits = preg_replace('/\D+/', '', $phone) ?? '';
if (strlen($phoneDigits) < 10 || strlen($phoneDigits) > 11) {
    respond(422, ['ok' => false, 'message' => 'Укажите корректный телефон.']);
}
if (!$consent) {
    respond(422, ['ok' => false, 'message' => 'Нужно согласие на обработку персональных данных.']);
}
if (text_length($message) > 800) {
    respond(422, ['ok' => false, 'message' => 'Комментарий должен быть не длиннее 800 символов.']);
}

$rateDir = $storageRoot . '/rate';
$submissionsDir = $storageRoot . '/submissions';
$logsDir = $storageRoot . '/logs';
foreach ([$rateDir, $submissionsDir, $logsDir] as $directory) {
    if (!is_dir($directory) && !mkdir($directory, 0750, true) && !is_dir($directory)) {
        respond(500, ['ok' => false, 'message' => 'Не удалось подготовить серверное хранилище.']);
    }
}

$clientIp = (string)($_SERVER['REMOTE_ADDR'] ?? 'unknown');
$rateKey = hash('sha256', $clientIp . '|' . ($_SERVER['HTTP_USER_AGENT'] ?? ''));
$rateFilePath = $rateDir . '/' . $rateKey . '.json';
$rateHandle = fopen($rateFilePath, 'c+');
if ($rateHandle === false || !flock($rateHandle, LOCK_EX)) {
    if (is_resource($rateHandle)) {
        fclose($rateHandle);
    }
    respond(503, ['ok' => false, 'message' => 'Сервис временно недоступен. Попробуйте позже.']);
}

$now = time();
$rawHistory = stream_get_contents($rateHandle);
$decodedHistory = is_string($rawHistory) && $rawHistory !== '' ? json_decode($rawHistory, true) : [];
$history = is_array($decodedHistory)
    ? array_values(array_filter($decodedHistory, static fn ($value): bool => is_int($value) && ($now - $value) < RATE_WINDOW_SECONDS))
    : [];

if (count($history) >= RATE_LIMIT) {
    flock($rateHandle, LOCK_UN);
    fclose($rateHandle);
    respond(429, ['ok' => false, 'message' => 'Слишком много заявок за короткое время. Попробуйте позже.']);
}

$history[] = $now;
rewind($rateHandle);
ftruncate($rateHandle, 0);
fwrite($rateHandle, (string)json_encode($history, JSON_UNESCAPED_UNICODE));
fflush($rateHandle);
flock($rateHandle, LOCK_UN);
fclose($rateHandle);
@chmod($rateFilePath, 0640);

$entry = [
    'id' => bin2hex(random_bytes(12)),
    'createdAt' => gmdate('c'),
    'formType' => $formType,
    'name' => $name,
    'phone' => $phone,
    'message' => $message,
    'ipHash' => hash('sha256', $clientIp),
    'userAgent' => substr(clean_text((string)($_SERVER['HTTP_USER_AGENT'] ?? '')), 0, 250),
];

$filename = $submissionsDir . '/' . gmdate('Ymd_His') . '_' . $entry['id'] . '.json';
$encodedEntry = json_encode($entry, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
if ($encodedEntry === false || file_put_contents($filename, $encodedEntry, LOCK_EX) === false) {
    respond(500, ['ok' => false, 'message' => 'Не удалось сохранить заявку.']);
}
@chmod($filename, 0640);

$logLine = sprintf("[%s] %s %s\n", gmdate('c'), $entry['formType'], $entry['id']);
file_put_contents($logsDir . '/contact.log', $logLine, FILE_APPEND | LOCK_EX);

$formNames = [
    'quiz' => 'Квиз / расчёт стоимости',
    'contacts' => 'Форма в разделе контактов',
    'modal' => 'Всплывающая форма',
];
$formName = $formNames[$formType] ?? $formType;

$telegramText = "📩 <b>НОВАЯ ЗАЯВКА С САЙТА</b>\n\n";
$telegramText .= "👤 <b>Имя:</b> " . tg_escape($name) . "\n";
$telegramText .= "📞 <b>Телефон:</b> " . tg_escape($phone) . "\n";
$telegramText .= "📋 <b>Форма:</b> " . tg_escape($formName) . "\n";

if ($message !== '') {
    $telegramText .= "\n📝 <b>Данные заявки:</b>\n" . tg_escape($message) . "\n";
}

$telegramText .= "\n🌐 <b>Источник:</b> Мардан Строй";

$telegramResult = send_to_telegram($telegramText);
if (!$telegramResult['ok']) {
    error_log('Telegram send failed: ' . $telegramResult['error']);
    respond(502, [
        'ok' => false,
        'message' => 'Telegram: ' . $telegramResult['error'],
    ]);
}

respond(200, [
    'ok' => true,
    'message' => 'Спасибо! Заявка отправлена. Мы свяжемся с вами в ближайшее рабочее время.',
]);
