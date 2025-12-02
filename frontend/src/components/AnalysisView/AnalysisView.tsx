import React from 'react';
import { FiFileText, FiAlertTriangle, FiTrendingUp, FiUsers, FiXCircle, FiInfo, FiCheckSquare, FiList } from 'react-icons/fi';
import { AnalysisData } from '../../types';
import TenderCard from '../TenderCard/TenderCard';
import TenderChat from '../TenderChat/TenderChat';
import styles from './AnalysisView.module.css';

interface AnalysisViewProps {
  data: AnalysisData;
}

const formatRiskFlag = (flag: string): string => {
  return flag
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

const AnalysisView: React.FC<AnalysisViewProps> = ({ data }) => {
  const keyFields = (data.ai_analysis.key_fields || {}) as Record<string, string>;
  const technicalAnalysis = (data.ai_analysis.technical_analysis || {}) as AnalysisData['ai_analysis']['technical_analysis'];
  const contractTerms = (data.ai_analysis.contract_terms_detail || {}) as Record<string, string>;
  const aiSimilarTenders = Array.isArray(data.ai_analysis.similar_tenders)
    ? data.ai_analysis.similar_tenders
    : [];

  return (
    <div className={styles.analysisView}>
      <div className={styles.card}>
        <h2 className={styles.tenderTitle}>{data.tender.name}</h2>
        <div className={styles.tenderNumber}>{data.tender.announce_number}</div>
        <div className={styles.tenderMeta}>
          <span>Заказчик: {data.tender.organizer_name}</span>
          <span className={styles.sum}>
            {(data.tender.total_sum / 1000000).toFixed(1)} млн ₸
          </span>
        </div>
      </div>

      <div className={styles.card}>
        <h3 className={styles.sectionTitle}>
          <FiFileText /> Краткое резюме
        </h3>
        <p className={styles.summary}>
          {data.ai_analysis.summary || 'Анализ тендера показывает основные требования...'}
        </p>
      </div>

      {Object.keys(keyFields).length > 0 && (
        <div className={styles.card}>
          <h3 className={styles.sectionTitle}>
            <FiInfo className={styles.infoIcon} /> Основная информация
          </h3>
          <div className={styles.keyFieldsGrid}>
            {keyFields.title && (
              <div className={styles.keyField}>
                <div className={styles.keyFieldLabel}>Название:</div>
                <div className={styles.keyFieldValue}>{keyFields.title}</div>
              </div>
            )}
            {keyFields.customer && (
              <div className={styles.keyField}>
                <div className={styles.keyFieldLabel}>Заказчик:</div>
                <div className={styles.keyFieldValue}>{keyFields.customer}</div>
              </div>
            )}
            {keyFields.budget && (
              <div className={styles.keyField}>
                <div className={styles.keyFieldLabel}>Бюджет:</div>
                <div className={styles.keyFieldValue}>{keyFields.budget}</div>
              </div>
            )}
            {keyFields.deadline && (
              <div className={styles.keyField}>
                <div className={styles.keyFieldLabel}>Срок подачи заявок:</div>
                <div className={styles.keyFieldValue}>{keyFields.deadline}</div>
              </div>
            )}
            {keyFields.subject && (
              <div className={styles.keyField}>
                <div className={styles.keyFieldLabel}>Предмет закупки:</div>
                <div className={styles.keyFieldValue}>{keyFields.subject}</div>
              </div>
            )}
            {keyFields.evaluation_criteria && (
              <div className={styles.keyField}>
                <div className={styles.keyFieldLabel}>Критерии оценки:</div>
                <div className={styles.keyFieldValue}>{keyFields.evaluation_criteria}</div>
              </div>
            )}
          </div>
        </div>
      )}

      {keyFields.technical_requirements && (
        <div className={styles.card}>
          <h3 className={styles.sectionTitle}>
            <FiCheckSquare className={styles.checkIcon} /> Технические требования
          </h3>
          <p className={styles.technicalText}>{keyFields.technical_requirements}</p>
        </div>
      )}

      {technicalAnalysis.technical_spec_table &&
       Array.isArray(technicalAnalysis.technical_spec_table) &&
       technicalAnalysis.technical_spec_table.length > 0 && (
        <div className={styles.card}>
          <h3 className={styles.sectionTitle}>
            <FiList /> Технические характеристики
          </h3>
          <div className={styles.tableWrapper}>
            <table className={styles.specTable}>
              <thead>
                <tr>
                  <th>Параметр</th>
                  <th>Значение</th>
                  <th>Примечания</th>
                </tr>
              </thead>
              <tbody>
                {(technicalAnalysis.technical_spec_table || []).map((spec, idx) => (
                  <tr key={idx}>
                    <td>{spec.parameter || '-'}</td>
                    <td>{spec.value || '-'}</td>
                    <td>{spec.notes || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {Object.keys(contractTerms).length > 0 && (
        <div className={styles.card}>
          <h3 className={styles.sectionTitle}>
            <FiFileText /> Условия договора
          </h3>
          <div className={styles.contractTermsList}>
            {contractTerms.deadlines && (
              <div className={styles.contractTerm}>
                <strong>Сроки выполнения:</strong> {contractTerms.deadlines}
              </div>
            )}
            {contractTerms.penalties && (
              <div className={styles.contractTerm}>
                <strong>Штрафы/пени:</strong> {contractTerms.penalties}
              </div>
            )}
            {contractTerms.warranties && (
              <div className={styles.contractTerm}>
                <strong>Гарантийные обязательства:</strong> {contractTerms.warranties}
              </div>
            )}
            {contractTerms.other_terms && (
              <div className={styles.contractTerm}>
                <strong>Другие условия:</strong> {contractTerms.other_terms}
              </div>
            )}
          </div>
        </div>
      )}

      {data.ai_analysis.risk_analysis && data.ai_analysis.risk_analysis.length > 0 && (
        <div className={styles.card}>
          <h3 className={styles.sectionTitle}>
            <FiAlertTriangle className={styles.warningIcon} /> Анализ рисков
          </h3>
          <div className={styles.risksList}>
            {data.ai_analysis.risk_analysis.map((risk, idx) => (
              <div key={`risk-${idx}`} className={styles.riskItem}>
                <div className={styles.riskHeader}>
                  <span className={styles.riskFlag}>{formatRiskFlag(risk.risk_flag)}</span>
                  <span className={styles.severity}>
                    Серьезность: {risk.severity}/100
                  </span>
                </div>
                <div className={styles.riskExplanation}>{risk.explanation}</div>
                {risk.justification && (
                  <div className={styles.riskJustification}>
                    <strong>Обоснование:</strong> {risk.justification}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {aiSimilarTenders.length > 0 && (
        <div className={styles.card}>
          <h3 className={styles.sectionTitle}>
            <FiFileText className={styles.documentIcon} /> Упоминания похожих тендеров в документе
          </h3>
          <div className={styles.aiSimilarList}>
            {aiSimilarTenders.map((tender: AnalysisData['ai_analysis']['similar_tenders'][number], idx: number) => (
              <div key={`ai-similar-${idx}`} className={styles.aiSimilarItem}>
                {tender.title && <div className={styles.aiSimilarTitle}>{String(tender.title)}</div>}
                {tender.customer && <div className={styles.aiSimilarCustomer}>Заказчик: {String(tender.customer)}</div>}
                {tender.price && <div className={styles.aiSimilarPrice}>Цена: {String(tender.price)}</div>}
                {tender.status && <div className={styles.aiSimilarStatus}>Статус: {String(tender.status)}</div>}
                {tender.notes && <div className={styles.aiSimilarNotes}>{String(tender.notes)}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {data.similar_tenders && data.similar_tenders.length > 0 && (
        <div className={styles.card}>
          <h3 className={styles.sectionTitle}>
            <FiTrendingUp className={styles.trendingIcon} /> Похожие тендеры в системе
          </h3>
          <div className={styles.similarGrid}>
            {data.similar_tenders.slice(0, 3).map((tender) => (
              <TenderCard
                key={`similar-${tender.id}`}
                tender={tender}
                onClick={() => console.log('Clicked similar tender:', tender.id)}
              />
            ))}
          </div>
        </div>
      )}

      {data.matching_suppliers && data.matching_suppliers.length > 0 && (
        <div className={styles.card}>
          <h3 className={styles.sectionTitle}>
            <FiUsers className={styles.usersIcon} /> Подходящие поставщики
          </h3>
          <div className={styles.suppliersList}>
            {data.matching_suppliers.map((supplier, idx) => {
              const bin = supplier.external_id || supplier.bin;
              const supplierUrl = bin
                ? `https://zakup.sk.kz/eprocglobal/open-api/suppliers?identifier=${bin}`
                : null;

              return (
                <div key={`supplier-${idx}-${bin || idx}`} className={styles.supplierItem}>
                  <div className={styles.supplierName}>
                    {supplierUrl ? (
                      <a
                        href={supplierUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.supplierLink}
                      >
                        {supplier.general_name || supplier.name || 'Поставщик'}
                      </a>
                    ) : (
                      <span>{supplier.general_name || supplier.name || 'Поставщик'}</span>
                    )}
                  </div>
                  <div className={styles.supplierDescription}>
                    {supplier.specialty_description || supplier.activity_description}
                  </div>
                  {supplier.distance && (
                    <div className={styles.match}>
                      Совпадение: {(100 - supplier.distance * 100).toFixed(0)}%
                    </div>
                  )}
                  {bin && (
                    <div className={styles.bin}>БИН/ИИН: {bin}</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {data.risk_suppliers && data.risk_suppliers.length > 0 && (
        <div className={styles.card}>
          <h3 className={`${styles.sectionTitle} ${styles.dangerTitle}`}>
            <FiXCircle /> Поставщики из черного списка
          </h3>
          <div className={styles.riskSuppliersList}>
            {data.risk_suppliers.map((supplier, idx) => (
              <div key={`risk-supplier-${idx}-${supplier.external_id || supplier.bin || idx}`} className={styles.riskSupplierItem}>
                <div className={styles.riskSupplierName}>
                  {supplier.general_name || supplier.name}
                </div>
                <div className={styles.riskSupplierWarning}>
                  Недобросовестный поставщик - {supplier.source_registry}
                </div>
                {supplier.external_id && (
                  <div className={styles.bin}>БИН/ИИН: {supplier.external_id}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {data.ai_analysis.final_notes && (
        <div className={styles.card}>
          <h3 className={styles.sectionTitle}>Заключение эксперта</h3>
          <p className={styles.finalNotes}>{data.ai_analysis.final_notes}</p>
        </div>
      )}

      <div className={styles.chatSection}>
        <TenderChat analysis={data.ai_analysis} />
      </div>
    </div>
  );
};

export default AnalysisView;