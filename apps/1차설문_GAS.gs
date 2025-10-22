/********************************************************
 * 유아플랜 1차 설문 수집 + 상태 드롭다운/색상 + 토큰 발급/검증 API (UUID 포함 완성본)
 * + 통합 조회 기능 + 정책자금 결과 저장 API + 텔레그램 알림
 * - 1차 설문 저장 (doPost, action 없음) - "1차설문" 단일 시트 사용
 * - 2차 토큰 API (validate/consume) : GET/POST 모두 지원
 * - 통합 조회 API (get_integrated_view) : 1차+2차+3차 데이터 통합 반환
 * - 정책자금 결과 저장 API (save_result) : "정책자금결과" 시트에 저장
 * - AccessTokens 시트: 발급/검증/소진 (uuid 필드 추가)
 * - 텔레그램 알림: 1차 설문 제출 시 실시간 알림
 * - 메뉴: 유아플랜 도구 ▸ 2차 초대 링크 발급(6h/12h/24h)
 ********************************************************/

/* ========= 공통 환경 ========= */
const API_TOKEN = 'youareplan';                 // 1차 수집/검증 공용 키
const TIMEZONE  = 'Asia/Seoul';
const RENDER_BASE_URL = 'https://survey2.youareplan.co.kr'; // 초대 링크 베이스

/* ========= ★★★ 텔레그램 알림 설정 ★★★ ========= */
const TELEGRAM_BOT_TOKEN = '8475264602:AAFQLZN6XAzPDZofqvYRrvz5liWUFdD8RDM';
const TELEGRAM_CHAT_ID = '7518089474';
const FIRST_SHEET_URL = 'https://docs.google.com/spreadsheets/d/118zWXL_jyTTcpXU4ljSPQrON-y1MPAGiZOBOkOcJWTk';

/* ========= ★★★ 2차, 3차 스프레드시트 ID (실제 ID로 교체 완료) ========= */
const SECOND_SURVEY_SHEET_ID = '10SqLY02gR1vUdkO12ss_WU8ALIEYMQMb2pqgfxt7LZo';
const THIRD_SURVEY_SHEET_ID = '1UwfACtxDU7BQM_lwuOKtlosdV8xBiXZ-aaJBfhh9FNc';

/* ========= 1차 시트 컬럼/레이아웃 ========= */
const FIRST_SHEET_NAME = '1차설문'; // ★ 단일 시트명
const HEADERS = [
  '접수번호','접수일시','이름','연락처','전화하기','이메일',
  '지역','업종','사업자형태','직원수','매출','필요자금',
  '정책자금경험','세금체납','금융연체','영업상태',
  '개인정보동의','마케팅동의','상태','위험신호',
  'UUID'
];
const COL_WIDTHS = [150,170,120,140,110,140,90,130,110,80,110,120,130,100,100,110,95,95,80,110,200];
const COL = {
  receipt:1, ts:2, name:3, phone:4, call:5, email:6,
  region:7, industry:8, bizType:9, emp:10, sales:11, need:12,
  policyExp:13, tax:14, credit:15, bizStat:16,
  privacy:17, marketing:18, status:19, risk:20, uuid:21
};

/* ========= 정책자금결과 시트 컬럼 ========= */
const RESULT_SHEET_NAME = '정책자금결과';
const RESULT_HEADERS = [
  '접수번호','정책자금명','승인금액(만원)','상담메모','결과저장일시',
  '고객명','연락처','업종','1차_필요자금','1차_세금체납','1차_금융연체',
  '2차_사업자명','2차_매출_올해','2차_자본금','2차_부채',
  '3차_담보보증요약','3차_리스크TOP3','3차_코치메모'
];
const RESULT_COL_WIDTHS = [150,200,120,300,170,120,140,130,120,100,100,160,120,120,120,220,220,220];

/* ========= AccessTokens 시트 정의 ========= */
const TOK_SHEET_NAME = 'AccessTokens';
const TOK_HEADERS = [
  'token','parent_receipt_no','phone_last4','preset_hours',
  'issued_at','expires_at','used_at','status','issued_by','uuid'
];

/* ========= ★★★ 텔레그램 알림 함수 ★★★ ========= */
function sendTelegramNotification(data) {
  try {
    const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;

    const message = `📋 <b>1차 설문 제출 알림</b>

👤 <b>고객 정보</b>
• 성함: ${data.name || '미입력'}
• 연락처: ${data.phone || '미입력'}
• 이메일: ${data.email || '미입력'}

🏢 <b>사업 정보</b>
• 지역: ${data.region || '미입력'}
• 업종: ${data.industry || '미입력'}
• 사업형태: ${data.business_type || '미입력'}
• 직원수: ${data.employee_count || '미입력'}
• 매출: ${data.revenue || '미입력'}
• 필요자금: ${data.funding_amount || '미입력'}

⚠️ <b>자격 현황</b>
• 세금체납: ${data.tax_status || '체납 없음'}
• 금융연체: ${data.credit_status || '연체 없음'}
• 영업상태: ${data.business_status || '정상 영업'}

🎫 접수번호: <code>${data.receipt_no || ''}</code>
⏰ 제출시간: ${data.timestamp || ''}

<a href="${FIRST_SHEET_URL}">📊 1차 시트 확인</a>`;

    const payload = {
      chat_id: TELEGRAM_CHAT_ID,
      text: message,
      parse_mode: 'HTML',
      disable_web_page_preview: false
    };

    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    const response = UrlFetchApp.fetch(url, options);
    const result = JSON.parse(response.getContentText());

    if (result.ok) {
      console.log('[텔레그램] 알림 전송 성공');
      return true;
    } else {
      console.log('[텔레그램] 전송 실패:', result.description);
      return false;
    }

  } catch (error) {
    console.log('[텔레그램] 오류:', error.toString());
    return false;
  }
}

/* ========= 엔드포인트 ========= */
// 1) POST: 설문 저장(기본) / 토큰 validate, consume(POST JSON) / 통합 조회 / 결과 저장
function doPost(e) {
  try {
    const body = JSON.parse(e.postData?.contents || '{}');

    // ---- 신규 1차 설문 저장 ----
    if (body.action == null) {
      if (body.token !== API_TOKEN) return _json({ status:'error', message:'인증 실패' });
      return _json(_handleSurveyPost(body)); // {status, receipt_no, uuid}
    }

    // ---- 토큰 API (validate / consume) ----
    if (body.api_token !== API_TOKEN) return _json({ ok:false, error:'forbidden' });

    const action = String(body.action || '').toLowerCase();
    if (action === 'validate') return _json(_validateToken(body.token));
    if (action === 'consume')  return _json(_consumeToken(body.token, body.parent));

    // ---- ★★★ 통합 조회 API ★★★ ----
    if (action === 'get_integrated_view') {
      return _json(getIntegratedView(body.receipt_no, body.api_token));
    }

    // ---- ★★★ 정책자금 결과 저장 API ★★★ ----
    if (action === 'save_result') {
      return _json(saveResult(body));
    }

    return _json({ ok:false, error:'unknown_action' });

  } catch (err) {
    return _json({ status:'error', message:String(err) });
  }
}

// 2) GET: 호환용 validate/consume (쿼리스트링)
function doGet(e) {
  try {
    const p = e.parameter || {};
    if (p.api_token !== API_TOKEN) return _json({ ok:false, error:'forbidden' });

    const action = String(p.action || '').toLowerCase();
    if (action === 'validate') return _json(_validateToken(p.token));
    if (action === 'consume')  return _json(_consumeToken(p.token, p.parent));

    // ---- ★★★ 통합 조회 GET 지원 ★★★ ----
    if (action === 'get_integrated_view') {
      return _json(getIntegratedView(p.receipt_no, p.token));
    }

    return _json({ ok:false, error:'unknown_action' });

  } catch (err) {
    return _json({ ok:false, error:String(err) });
  }
}

/* ========= ★★★ 정책자금 결과 저장 함수 (신규 추가) ★★★ ========= */
function saveResult(body) {
  // 토큰 검증
  if (body.api_token !== API_TOKEN) {
    return { status: "error", message: "Invalid token" };
  }

  const receiptNo = String(body.receipt_no || '').trim();
  const policyName = String(body.policy_name || '').trim();
  const approvedAmount = String(body.approved_amount || '').trim();
  const resultMemo = String(body.result_memo || '').trim();

  if (!receiptNo || !policyName || !approvedAmount) {
    return { status: "error", message: "접수번호, 정책자금명, 승인금액은 필수입니다" };
  }

  try {
    // 1차+2차+3차 데이터 조회
    const integratedData = getIntegratedView(receiptNo, body.api_token);
    if (integratedData.status !== "success") {
      return { status: "error", message: "통합 데이터 조회 실패: " + integratedData.message };
    }

    const data = integratedData.data;
    const stage1 = data.stage1 || {};
    const stage2 = data.stage2 || {};
    const stage3 = data.stage3 || {};

    // 정책자금결과 시트 준비
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const resultSheet = _ensureResultSheet(ss);

    // 기존 동일한 접수번호+정책자금명 찾기
    const existingRow = _findResultRow(resultSheet, receiptNo, policyName);

    const now = new Date();
    const nowDisp = Utilities.formatDate(now, TIMEZONE, 'yyyy. M. d. a h:mm:ss');

    // 결과 행 데이터 구성
    const rowData = [
      receiptNo,
      policyName,
      approvedAmount,
      resultMemo,
      nowDisp,
      stage1.name || '',
      stage1.phone || '',
      stage1.industry || '',
      stage1.funding_amount || '',
      stage1.tax_status || '',
      stage1.credit_status || '',
      stage2.business_name || '',
      stage2.revenue_y1 || '',
      stage2.capital_amount || '',
      stage2.debt_amount || '',
      stage3.collateral_profile || '',
      stage3.risk_top3 || '',
      stage3.coach_notes || ''
    ];

    if (existingRow) {
      // 기존 행 업데이트
      resultSheet.getRange(existingRow, 1, 1, RESULT_HEADERS.length).setValues([rowData]);
    } else {
      // 새 행 추가
      resultSheet.appendRow(rowData);
    }

    _postFormatResultSheet(resultSheet);

    return {
      status: "success",
      message: existingRow ? "결과가 업데이트되었습니다" : "결과가 저장되었습니다",
      receipt_no: receiptNo,
      policy_name: policyName
    };

  } catch (error) {
    return { status: "error", message: error.toString() };
  }
}

/* ========= 정책자금결과 시트 관리 함수들 ========= */
function _ensureResultSheet(ss) {
  let sheet = ss.getSheetByName(RESULT_SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(RESULT_SHEET_NAME);
    sheet.getRange(1, 1, 1, RESULT_HEADERS.length).setValues([RESULT_HEADERS]);
    _paintResultHeader(sheet);
    for (let i = 0; i < RESULT_COL_WIDTHS.length; i++) {
      sheet.setColumnWidth(i + 1, RESULT_COL_WIDTHS[i]);
    }
    sheet.setFrozenRows(1);
    sheet.setRowHeight(1, 28);
  }
  return sheet;
}

function _paintResultHeader(sheet) {
  sheet.getRange(1, 1, 1, RESULT_HEADERS.length)
    .setFontFamily('Noto Sans KR')
    .setFontSize(11)
    .setFontWeight('bold')
    .setHorizontalAlignment('center')
    .setBackground('#d9e1f2')
    .setFontColor('#000000')
    .setBorder(false, false, true, false, false, false, '#9fb6d9', SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
}

function _postFormatResultSheet(sheet) {
  const lr = sheet.getLastRow();
  if (lr > 1) {
    sheet.setRowHeights(2, lr - 1, 24);
    sheet.getRange(2, 1, lr - 1, RESULT_HEADERS.length)
      .setWrap(false)
      .setBackground(null)
      .setFontSize(11)
      .setFontColor('#000000')
      .setNumberFormat('@');
  }
}

function _findResultRow(sheet, receiptNo, policyName) {
  const lr = sheet.getLastRow();
  if (lr < 2) return null;

  const data = sheet.getRange(2, 1, lr - 1, 2).getValues(); // 접수번호, 정책자금명
  for (let i = 0; i < data.length; i++) {
    if (String(data[i][0]).trim() === receiptNo && String(data[i][1]).trim() === policyName) {
      return i + 2;
    }
  }
  return null;
}

/* ========= ★★★ 통합 조회 함수 ★★★ ========= */
function getIntegratedView(receiptNo, token) {
  // 토큰 검증
  if (token !== API_TOKEN) {
    return { status: "error", message: "Invalid token" };
  }

  if (!receiptNo) {
    return { status: "error", message: "접수번호가 필요합니다" };
  }

  try {
    // 1차 데이터 가져오기 (현재 스프레드시트)
    const data1 = findRowByReceiptNo(SpreadsheetApp.getActiveSpreadsheet(), receiptNo, '1차');

    // 2차 데이터 가져오기 (다른 스프레드시트)
    let data2 = null;
    try {
      if (SECOND_SURVEY_SHEET_ID && SECOND_SURVEY_SHEET_ID !== 'YOUR_2ND_SURVEY_SPREADSHEET_ID_HERE') {
        const sheet2 = SpreadsheetApp.openById(SECOND_SURVEY_SHEET_ID);
        data2 = findRowByReceiptNo(sheet2, receiptNo, '2차');
      }
    } catch (e) {
      console.log("2차 시트 접근 실패:", e);
    }

    // 3차 데이터 가져오기 (다른 스프레드시트)
    let data3 = null;
    try {
      if (THIRD_SURVEY_SHEET_ID && THIRD_SURVEY_SHEET_ID !== 'YOUR_3RD_SURVEY_SPREADSHEET_ID_HERE') {
        const sheet3 = SpreadsheetApp.openById(THIRD_SURVEY_SHEET_ID);
        data3 = findRowByReceiptNo(sheet3, receiptNo, '3차');
      }
    } catch (e) {
      console.log("3차 시트 접근 실패:", e);
    }

    // 통합 데이터 구성
    const integrated = {
      receipt_no: receiptNo,
      stage1: data1 ? {
        name: data1.name || '',
        phone: data1.phone || '',
        email: data1.email || '',
        region: data1.region || '',
        industry: data1.industry || '',
        business_type: data1.business_type || '',
        employee_count: data1.employee_count || '',
        revenue: data1.revenue || '',
        funding_amount: data1.funding_amount || '',
        policy_experience: data1.policy_experience || '',
        tax_status: data1.tax_status || '',
        credit_status: data1.credit_status || '',
        business_status: data1.business_status || '',
        completed_at: data1.timestamp || ''
      } : null,
      stage2: data2 ? {
        business_name: data2.business_name || '',
        startup_date: data2.startup_date || '',
        revenue_y1: data2.revenue_y1 || '',
        revenue_y2: data2.revenue_y2 || '',
        revenue_y3: data2.revenue_y3 || '',
        capital_amount: data2.capital_amount || '',
        debt_amount: data2.debt_amount || '',
        biz_reg_no: data2.biz_reg_no || '',
        completed_at: data2.timestamp || ''
      } : null,
      stage3: data3 ? {
        collateral_profile: data3.collateral_profile || '',
        tax_credit_summary: data3.tax_credit_summary || '',
        loan_summary: data3.loan_summary || '',
        docs_check: data3.docs_check || '',
        priority_exclusion: data3.priority_exclusion || '',
        risk_top3: data3.risk_top3 || '',
        coach_notes: data3.coach_notes || '',
        completed_at: data3.timestamp || ''
      } : null,
      progress_pct: calculateProgress(data1, data2, data3),
      server_version: 1,
      last_updated: _toIso_(new Date())
    };

    return { status: "success", data: integrated };

  } catch (error) {
    return { status: "error", message: error.toString() };
  }
}

function findRowByReceiptNo(spreadsheet, receiptNo, surveyType) {
  if (!receiptNo || !spreadsheet) return null;

  try {
    // 1차: "1차설문" 시트에서 검색 (★ 수정됨)
    if (surveyType === '1차') {
      const sheet = spreadsheet.getSheetByName(FIRST_SHEET_NAME);
      if (!sheet) return null;

      const lr = sheet.getLastRow();
      if (lr < 2) return null;

      const data = sheet.getRange(2, 1, lr - 1, HEADERS.length).getValues();
      for (let i = 0; i < data.length; i++) {
        if (String(data[i][0]).trim() === receiptNo) {
          return {
            name: data[i][2],
            phone: data[i][3],
            email: data[i][5],
            region: data[i][6],
            industry: data[i][7],
            business_type: data[i][8],
            employee_count: data[i][9],
            revenue: data[i][10],
            funding_amount: data[i][11],
            policy_experience: data[i][12],
            tax_status: data[i][13],
            credit_status: data[i][14],
            business_status: data[i][15],
            timestamp: data[i][1]
          };
        }
      }
    }

    // 2차, 3차: 단일 시트에서 검색 (★ 수정됨)
    else {
      let sheetName = '';
      if (surveyType === '2차') sheetName = '2차설문';
      if (surveyType === '3차') sheetName = '3차설문';

      const sheet = spreadsheet.getSheetByName(sheetName);
      if (!sheet) return null;

      const lr = sheet.getLastRow();
      if (lr < 2) return null;

      const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
      const receiptCol = headers.indexOf('parent_receipt_no') !== -1 ?
                         headers.indexOf('parent_receipt_no') :
                         headers.indexOf('접수번호');

      if (receiptCol === -1) return null;

      const data = sheet.getRange(2, 1, lr - 1, headers.length).getValues();
      for (let i = 0; i < data.length; i++) {
        if (String(data[i][receiptCol]).trim() === receiptNo) {
          const rowData = {};
          headers.forEach((header, index) => {
            rowData[header] = data[i][index];
          });

          // 2차 설문 필드 매핑
          if (surveyType === '2차') {
            return {
              business_name: rowData['사업자명'] || '',
              startup_date: rowData['사업시작일'] || '',
              revenue_y1: rowData['매출_올해(만원)'] || '',
              revenue_y2: rowData['매출_전년(만원)'] || '',
              revenue_y3: rowData['매출_전전년(만원)'] || '',
              capital_amount: rowData['자본금(만원)'] || '',
              debt_amount: rowData['부채(만원)'] || '',
              biz_reg_no: rowData['사업자등록번호'] || '',
              timestamp: rowData['접수일시'] || ''
            };
          }

          // 3차 설문 필드 매핑
          if (surveyType === '3차') {
            return {
              collateral_profile: rowData['담보·보증 요약'] || '',
              tax_credit_summary: rowData['세무·신용 요약'] || '',
              loan_summary: rowData['대출/자금 현황'] || '',
              docs_check: rowData['준비 서류 체크'] || '',
              priority_exclusion: rowData['우대/제외 요건'] || '',
              risk_top3: rowData['리스크 Top3'] || '',
              coach_notes: rowData['코치 메모(전용)'] || '',
              timestamp: rowData['3차제출일시'] || ''
            };
          }

          return rowData;
        }
      }
    }

  } catch (error) {
    console.log(`${surveyType} 데이터 조회 실패:`, error);
  }

  return null;
}

function calculateProgress(data1, data2, data3) {
  let progress = 0;
  if (data1) progress += 33;
  if (data2) progress += 33;
  if (data3) progress += 34;
  return progress;
}

/* ========= 1차 설문 저장 로직 (★★★ 텔레그램 알림 추가) ========= */
function _handleSurveyPost(body) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = _ensureSheet_(ss, FIRST_SHEET_NAME); // ★ 단일 시트 사용
  _ensureHeader_(sheet);
  _ensureSheetLayout_(sheet);

  const now = new Date();
  const ts  = Utilities.formatDate(now, TIMEZONE, 'yyyy. M. d. a h:mm:ss');
  const receiptNo = body.receipt_no || _makeReceiptNo_(now);

  const risks = [];
  const taxS = body.tax_status || '체납 없음';
  const creS = body.credit_status || '연체 없음';
  const bizS = body.business_status || '정상 영업';
  if (taxS !== '체납 없음') risks.push('체납');
  if (creS !== '연체 없음') risks.push('연체');
  if (bizS !== '정상 영업') risks.push('휴/폐업');

  // ★ 신규: UUID 생성
  const uuid = Utilities.getUuid();

  const row = [
    receiptNo, ts, body.name||'', body.phone||'', '', body.email||'미입력',
    body.region||'', body.industry||'', body.business_type||'', body.employee_count||'',
    body.revenue||'', body.funding_amount||'', body.policy_experience||'경험 없음',
    taxS, creS, bizS,
    body.privacy_agree ? 'Y' : '', body.marketing_agree ? 'Y' : '',
    '신규', risks.join(', '),
    uuid // ★ 마지막 컬럼에 UUID 저장
  ];

  sheet.appendRow(row);
  _postFormatLastRow_(sheet);

  // ★★★ 텔레그램 알림 전송 ★★★
  try {
    sendTelegramNotification({
      name: body.name || '',
      phone: body.phone || '',
      email: body.email || '미입력',
      region: body.region || '',
      industry: body.industry || '',
      business_type: body.business_type || '',
      employee_count: body.employee_count || '',
      revenue: body.revenue || '',
      funding_amount: body.funding_amount || '',
      tax_status: taxS,
      credit_status: creS,
      business_status: bizS,
      receipt_no: receiptNo,
      timestamp: ts
    });
  } catch (notifyError) {
    // 알림 실패해도 저장은 성공으로 처리
    console.log('[텔레그램 알림 오류]', notifyError);
  }

  return { status:'success', receipt_no: receiptNo, uuid };
}

/* ========= 토큰 검증/소진 ========= */
function _validateToken(token) {
  const rec = _getTokenRecord(token);
  if (!rec) return { ok:false, error:'not_found' };
  if (rec.status !== 'issued') return { ok:false, error:'used_or_revoked' };

  const now = _now();
  const exp = _parseDateMaybe(rec.expires_at);
  if (!exp) return { ok:false, error:'expired_or_invalid_date' };
  if (now > exp) return { ok:false, error:'expired' };

  // 1차 상태 = '계약' 확인
  const found = _findFirstSurveyStatus_(rec.parent_receipt_no);
  if (!found) return { ok:false, error:'parent_not_found' };
  if (String(found.status).trim() !== '계약') return { ok:false, error:'parent_not_contract' };

  const remainSec = Math.max(0, Math.floor((exp - now)/1000));
  return {
    ok:true,
    parent_receipt_no: rec.parent_receipt_no,
    phone_mask: rec.phone_last4 ? `***-****-${rec.phone_last4}` : '',
    expires_at: rec.expires_at,
    remaining_seconds: remainSec,
    uuid: rec.uuid || ''
  };
}

function _consumeToken(token, parent) {
  const lock = LockService.getScriptLock();
  lock.tryLock(5000);
  try {
    const rec = _getTokenRecord(token, true);
    if (!rec) return { ok:false, error:'not_found' };
    if (rec.status !== 'issued') return { ok:false, error:'used_or_revoked' };

    const now = _now();
    const exp = _parseDateMaybe(rec.expires_at);
    if (!exp) return { ok:false, error:'expired_or_invalid_date' };
    if (now > exp) return { ok:false, error:'expired' };
    if (parent && parent !== rec.parent_receipt_no) return { ok:false, error:'parent_mismatch' };

    const sh = _ensureTokenSheet_();
    sh.getRange(rec._row, 7).setValue(_toIso_(now)); // used_at (ISO)
    sh.getRange(rec._row, 8).setValue('used');       // status
    return { ok:true, uuid: rec.uuid || '' };
  } finally {
    lock.releaseLock();
  }
}

/* ========= 토큰 시트 유틸 ========= */
function _ensureTokenSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(TOK_SHEET_NAME);
  if (!sh) {
    sh = ss.insertSheet(TOK_SHEET_NAME);
    sh.getRange(1,1,1,TOK_HEADERS.length).setValues([TOK_HEADERS]);
    sh.setFrozenRows(1);
    _hardenTokenSheetFormat_();
  } else {
    // 헤더 보정(누락 시 자동 정렬)
    const cur = sh.getRange(1,1,1,Math.max(sh.getLastColumn(), TOK_HEADERS.length)).getValues()[0];
    if (JSON.stringify(cur.slice(0, TOK_HEADERS.length)) !== JSON.stringify(TOK_HEADERS)) {
      sh.getRange(1,1,1,TOK_HEADERS.length).setValues([TOK_HEADERS]);
    }
  }
  return sh;
}

function _getTokenRecord(token, withRow=false) {
  if (!token) return null;
  const sh = _ensureTokenSheet_();
  const lr = sh.getLastRow();
  if (lr < 2) return null;
  const rows = sh.getRange(2,1,lr-1,TOK_HEADERS.length).getValues();
  for (let i=0;i<rows.length;i++){
    if (String(rows[i][0]) === token) {
      const obj = {
        token: rows[i][0],
        parent_receipt_no: rows[i][1],
        phone_last4: rows[i][2],
        preset_hours: rows[i][3],
        issued_at: rows[i][4],
        expires_at: rows[i][5],
        used_at: rows[i][6],
        status: rows[i][7],
        issued_by: rows[i][8],
        uuid: rows[i][9] || ''
      };
      if (withRow) obj._row = i+2;
      return obj;
    }
  }
  return null;
}

/* ========= 메뉴 (유아플랜 도구) ========= */
function addYouArePlanMenus() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('유아플랜 도구')
    .addItem('1차설문 시트 레이아웃 정리', 'ReformatFirstSheet')
    .addItem('정책자금결과 시트 레이아웃 정리', 'ReformatResultSheet')
    .addSeparator()
    .addSubMenu(
      ui.createMenu('2차 초대 링크 발급')
        .addItem('발급(6시간)',  'IssueInvite6h')
        .addItem('발급(12시간)', 'IssueInvite12h')
        .addItem('발급(24시간)', 'IssueInvite24h')
    )
    .addSeparator()
    .addItem('텔레그램 알림 테스트', 'TestTelegramNotification')
    .addToUi();
}

// 시트 열릴 때 메뉴 붙이기
function onOpen() {
  addYouArePlanMenus();
}

// 발급 핸들러
function IssueInvite6h(){ _issueInvitePreset(6); }
function IssueInvite12h(){ _issueInvitePreset(12); }
function IssueInvite24h(){ _issueInvitePreset(24); }

function _issueInvitePreset(hours){
  try{
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName(FIRST_SHEET_NAME); // ★ 1차설문 시트 고정

    if (!sh) {
      SpreadsheetApp.getUi().alert('1차설문 시트를 찾을 수 없습니다.');
      return;
    }

    const sel = sh.getActiveCell();
    const r = sel ? sel.getRow() : 0;
    if (r < 2) { SpreadsheetApp.getUi().alert('데이터 행을 선택하고 실행하세요.'); return; }

    const header = sh.getRange(1,1,1,sh.getLastColumn()).getValues()[0];
    const receipt = String(sh.getRange(r, COL.receipt).getDisplayValue()).trim();
    const phone   = String(sh.getRange(r, COL.phone).getDisplayValue()).replace(/[^0-9]/g,'');
    const status  = String(sh.getRange(r, COL.status).getDisplayValue()).trim();

    if (!receipt) { SpreadsheetApp.getUi().alert('접수번호가 비어 있습니다.'); return; }
    if (status !== '계약') { SpreadsheetApp.getUi().alert('상태가 "계약"인 건만 초대 링크를 발급할 수 있습니다.'); return; }

    const last4 = phone ? phone.slice(-4) : '';
    const now = _now();
    const exp = new Date(now.getTime() + hours*60*60*1000);

    // ★ UUID 읽기
    const uuidCol = header.indexOf('UUID') + 1;
    const uuidVal = uuidCol > 0 ? String(sh.getRange(r, uuidCol).getDisplayValue()).trim() : '';

    // 토큰 생성 및 기록 (시간은 ISO로)
    const token = Utilities.getUuid().replace(/-/g,'');
    const tokSh = _ensureTokenSheet_();
    tokSh.appendRow([
      token, receipt, last4, hours,
      _toIso_(now), _toIso_(exp), '', 'issued', Session.getActiveUser().getEmail() || 'unknown',
      uuidVal
    ]);

    // 링크 생성: ?t= + ★ &u=uuid 포함
    const link = `${RENDER_BASE_URL}/?t=${encodeURIComponent(token)}${uuidVal ? `&u=${encodeURIComponent(uuidVal)}` : ''}`;
    SpreadsheetApp.getUi().alert(
      `초대 링크가 발급되었습니다.\n\n- 접수번호: ${receipt}\n- 유효시간: ${hours}h\n- 만료시각: ${_toIso_(exp)}\n\n링크:\n${link}`
    );
  } catch(err){
    SpreadsheetApp.getUi().alert('오류: ' + String(err));
  }
}

/* ========= ★★★ 텔레그램 알림 테스트 함수 ★★★ ========= */
function TestTelegramNotification() {
  const testData = {
    name: '테스트 고객',
    phone: '010-1234-5678',
    email: 'test@example.com',
    region: '서울',
    industry: '제조업',
    business_type: '법인사업자',
    employee_count: '5-9명',
    revenue: '1억원~3억원',
    funding_amount: '1-3억원',
    tax_status: '체납 없음',
    credit_status: '연체 없음',
    business_status: '정상 영업',
    receipt_no: 'YP20250000TEST',
    timestamp: Utilities.formatDate(new Date(), TIMEZONE, 'yyyy. M. d. a h:mm:ss')
  };

  const result = sendTelegramNotification(testData);

  if (result) {
    SpreadsheetApp.getUi().alert('✅ 텔레그램 알림 테스트 성공!\n\n텔레그램에서 메시지를 확인하세요.');
  } else {
    SpreadsheetApp.getUi().alert('❌ 텔레그램 알림 전송 실패\n\n로그를 확인하세요.');
  }
}

/* ========= 1차 시트 레이아웃/서식 ========= */
function _makeReceiptNo_(d) {
  const ymd = Utilities.formatDate(d, TIMEZONE, 'yyyyMMdd');
  const rnd = Math.floor(Math.random() * 9000) + 1000;
  return `YP${ymd}${rnd}`;
}
function _ensureSheet_(ss, name) {
  let sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);
  return sh;
}
function _ensureHeader_(sheet) {
  sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
  _paintHeader_(sheet);
  for (let i = 0; i < COL_WIDTHS.length; i++) sheet.setColumnWidth(i + 1, COL_WIDTHS[i]);
  const maxRows = sheet.getMaxRows();
  const maxCols = Math.max(sheet.getMaxColumns(), HEADERS.length);
  sheet.getRange(1, 1, maxRows, maxCols).setWrap(false).setFontFamily('Noto Sans KR');
}
function _ensureSheetLayout_(sheet) {
  sheet.setFrozenRows(1);
  sheet.setRowHeight(1, 28);
  const lr = sheet.getLastRow();
  if (lr > 1) sheet.setRowHeights(2, lr - 1, 24);
  if (lr >= 1) sheet.getRange(1, 1, lr, HEADERS.length).setWrap(false).setBackground(null).setFontColor('#000000');
  if (lr > 1) sheet.getRange(2, COL.ts, lr - 1, 1).setNumberFormat('@');
  _applyStatusValidationAndColors_(sheet);
}
function _postFormatLastRow_(sheet) {
  const lr = sheet.getLastRow();
  if (lr < 2) return;
  sheet.getRange(lr, 1, 1, HEADERS.length)
       .setWrap(false).setBackground(null).setFontSize(11).setFontColor('#000000');
  sheet.getRange(lr, COL.ts).setNumberFormat('@');
  const phoneA1 = `D${lr}`;
  sheet.getRange(lr, COL.call).setFormula(`=IF(LEN(${phoneA1})>0, HYPERLINK("tel:"&${phoneA1},"📞 전화하기"), "")`);
  _paintHeader_(sheet);
  _applyStatusValidationAndColors_(sheet);
}
function _paintHeader_(sheet){
  const rng = sheet.getRange(1,1,1,HEADERS.length);
  rng
    .setFontFamily('Noto Sans KR')
    .setFontSize(11)
    .setFontWeight('bold')
    .setHorizontalAlignment('center')
    .setBackground('#d9e1f2')
    .setFontColor('#000000')
    .setBorder(false, false, true, false, false, false, '#9fb6d9', SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
}
function _applyStatusValidationAndColors_(sheet) {
  const statusRange = sheet.getRange('S2:S'); // 상태열 (19번째, 고정)
  const statusVals = ['신규','계약','보류','중단'];
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(statusVals, true)
    .setAllowInvalid(false)
    .build();
  statusRange.setDataValidation(rule);

  const rules = sheet.getConditionalFormatRules() || [];
  const statusA1 = statusRange.getA1Notation();
  const filtered = rules.filter(r => !r.getRanges().map(x=>x.getA1Notation()).includes(statusA1));

  const mkRule = (text, bg) =>
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo(text)
      .setBackground(bg)
      .setBold(true)
      .setRanges([statusRange])
      .build();

  filtered.push(mkRule('계약', '#E6F4EA'));
  filtered.push(mkRule('신규', '#F1F5F9'));
  filtered.push(mkRule('보류', '#FFF7CC'));
  filtered.push(mkRule('중단', '#FDE8E8'));

  sheet.setConditionalFormatRules(filtered);
}

// 레이아웃 정리 함수들 (메뉴용)
function ReformatFirstSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(FIRST_SHEET_NAME);
  if (sh) {
    _ensureHeader_(sh);
    _ensureSheetLayout_(sh);
    _convertBColumnToText_(sh);
    _backfillCallLinks_(sh);
    _applyRowHeightsAndWrap_(sh);
    _applyStatusValidationAndColors_(sh);
    SpreadsheetApp.getUi().alert('1차설문 시트 레이아웃을 정리했습니다.');
  } else {
    SpreadsheetApp.getUi().alert('1차설문 시트를 찾을 수 없습니다.');
  }
}

function ReformatResultSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = _ensureResultSheet(ss);
  _postFormatResultSheet(sh);
  SpreadsheetApp.getUi().alert('정책자금결과 시트 레이아웃을 정리했습니다.');
}

function _convertBColumnToText_(sheet) {
  const lr = sheet.getLastRow();
  if (lr < 2) return;
  const rng = sheet.getRange(2, COL.ts, lr - 1, 1);
  const display = rng.getDisplayValues();
  rng.setValues(display).setNumberFormat('@');
}
function _backfillCallLinks_(sheet) {
  const lr = sheet.getLastRow();
  if (lr < 2) return;
  for (let r = 2; r <= lr; r++) {
    const callCell = sheet.getRange(r, COL.call);
    if (!callCell.getDisplayValue()) {
      callCell.setFormula(`=IF(LEN(D${r})>0, HYPERLINK("tel:"&D${r},"📞 전화하기"), "")`);
    }
  }
}
function _applyRowHeightsAndWrap_(sheet) {
  const lr = sheet.getLastRow();
  if (lr > 1) {
    sheet.setRowHeights(2, lr - 1, 24);
    sheet.getRange(2, 1, lr - 1, HEADERS.length)
         .setWrap(false)
         .setBackground(null)
         .setFontColor('#000000');
  }
}

/* ========= 1차 상태 조회(토큰 검증용) ========= */
function _findFirstSurveyStatus_(receiptNo) {
  if (!receiptNo) return null;
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(FIRST_SHEET_NAME); // ★ 1차설문 시트에서만 검색
  if (!sh) return null;

  const lr = sh.getLastRow();
  if (lr < 2) return null;
  const vals = sh.getRange(2, 1, lr - 1, COL.status).getValues(); // A~S
  for (let i=0;i<vals.length;i++){
    const rec = String(vals[i][0]).trim();               // A열: 접수번호
    if (rec === receiptNo) {
      const st = String(vals[i][COL.status-1]).trim();   // S열: 상태
      return { status: st, sheetName: FIRST_SHEET_NAME };
    }
  }
  return null;
}

/* ========= 공통 유틸 ========= */
function _json(obj) { return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON); }
function _now(){ return new Date(); }
function _fmt(d){ return Utilities.formatDate(d, TIMEZONE, 'yyyy. M. d. a h:mm:ss'); }
function _toIso_(d){ return Utilities.formatDate(d, TIMEZONE, "yyyy-MM-dd'T'HH:mm:ssXXX"); }

// AccessTokens 시트 전체 텍스트서식(날짜 자동 변환 방지)
function _hardenTokenSheetFormat_(){
  const sh = _ensureTokenSheet_();
  sh.getRange(1,1,Math.max(sh.getMaxRows(),2),TOK_HEADERS.length).setNumberFormat('@');
}

// AccessTokens 만료일 파싱 보강(ISO/국문형 모두 허용)
function _parseDateMaybe(v){
  if (v instanceof Date) return v;
  const s = String(v||'').trim();
  if (!s) return null;

  // 1) ISO 시도
  const iso = new Date(s);
  if (!isNaN(iso.getTime())) return iso;

  // 2) "yyyy. M. d. a h:mm:ss" (오전/오후) 스타일 보정
  const t = s
    .replace(/\./g,' ')
    .replace(/\s+/g,' ')
    .replace('오전','AM')
    .replace('오후','PM')
    .trim();
  const d = new Date(t);
  return isNaN(d.getTime()) ? null : d;
}

// 호환성을 위한 기존 함수 (월별→단일 시트로 변경됨)
function ReformatAllMonthlySheets() {
  // 기존 월별 시트 방식에서 단일 시트로 변경되었습니다.
  ReformatFirstSheet();
  SpreadsheetApp.getUi().alert('1차설문 시트 레이아웃을 정리했습니다.\n\n참고: 월별 시트 방식에서 단일 "1차설문" 시트로 변경되었습니다.');
}

// ★ GAS 테스트 함수들
function testIntegratedView() {
  try {
    const result = getIntegratedView("YP20240914001", "youareplan");
    console.log("테스트 결과:", JSON.stringify(result, null, 2));
    return result;
  } catch (error) {
    console.log("테스트 오류:", error.toString());
    return { status: "error", message: error.toString() };
  }
}

function testSaveResult() {
  try {
    const testData = {
      api_token: "youareplan",
      receipt_no: "YP20240914001",
      policy_name: "벤처기업정책자금",
      approved_amount: "50000",
      result_memo: "테스트 승인 완료"
    };

    const result = saveResult(testData);
    console.log("결과 저장 테스트:", JSON.stringify(result, null, 2));
    return result;
  } catch (error) {
    console.log("결과 저장 테스트 오류:", error.toString());
    return { status: "error", message: error.toString() };
  }
}
