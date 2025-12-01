import React from 'react';
import { FiFileText, FiAlertTriangle, FiTrendingUp, FiUsers, FiXCircle } from 'react-icons/fi';
import { AnalysisData } from '../../types';
import TenderCard from '../TenderCard/TenderCard';
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

      {data.similar_tenders && data.similar_tenders.length > 0 && (
        <div className={styles.card}>
          <h3 className={styles.sectionTitle}>
            <FiTrendingUp className={styles.trendingIcon} /> Похожие тендеры
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

              return (
                <div key={`supplier-${idx}-${bin || idx}`} className={styles.supplierItem}>
                  <div className={styles.supplierName}>
                    <span>{supplier.general_name || supplier.name || 'Поставщик'}</span>
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
    </div>
  );
};

export default AnalysisView;