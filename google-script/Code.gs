/**
 * Приём заявок с сайта Vaxter Five.
 * Всё хранится на Google Диске: каждая заявка — строка в Google Таблице,
 * вложение — файл в папке «Заявки с сайта — файлы», в заявке ссылка на него.
 */
const SHEET_NAME = 'Заявки';
const FOLDER_NAME = 'Заявки с сайта — файлы';
const MAX_FILE_MB = 10;

function doPost(e) {
  try {
    const d = JSON.parse(e.postData.contents);
    if (d.website) return json({ ok: true }); // honeypot: бот заполнил скрытое поле

    const fileUrl = d.file ? saveFile(d.file) : '';
    const row = [new Date(), d.what, d.qty, d.date, d.design, d.mat, d.name, d.contact, fileUrl, d.page || '', d.consent ? 'Да' : ''];
    sheet().appendRow(row);

    return json({ ok: true });
  } catch (err) {
    return json({ ok: false, error: String(err) });
  }
}

function sheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(SHEET_NAME);
  if (!sh) {
    sh = ss.insertSheet(SHEET_NAME);
    sh.appendRow(['Дата', 'Что произвести', 'Количество', 'Срок', 'Дизайн', 'Материалы', 'Имя', 'Контакт', 'Файл', 'Страница', 'Согласие на ПД']);
    sh.setFrozenRows(1);
  }
  return sh;
}

function saveFile(f) {
  const bytes = Utilities.base64Decode(f.data);
  if (bytes.length > MAX_FILE_MB * 1024 * 1024) return 'файл больше ' + MAX_FILE_MB + ' МБ — не сохранён';
  // папка с файлами создаётся рядом с таблицей (в той же папке Диска), а не в корне
  const parent = DriveApp.getFileById(SpreadsheetApp.getActiveSpreadsheet().getId()).getParents().next();
  const it = parent.getFoldersByName(FOLDER_NAME);
  const folder = it.hasNext() ? it.next() : parent.createFolder(FOLDER_NAME);
  return folder.createFile(Utilities.newBlob(bytes, f.type, f.name)).getUrl();
}

function json(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

// Запустите вручную один раз из редактора, чтобы выдать разрешения (таблица и диск).
function testSetup() {
  sheet();
  DriveApp.getRootFolder();
  Logger.log('OK');
}
