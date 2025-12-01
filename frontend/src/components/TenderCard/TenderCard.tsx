import React from 'react';
import { BiBuilding } from 'react-icons/bi';
import { FiCheckCircle } from 'react-icons/fi';
import { Tender } from '../../types';
import styles from './TenderCard.module.css';

interface TenderCardProps {
  tender: Tender;
  onClick: () => void;
}

const TenderCard: React.FC<TenderCardProps> = ({ tender, onClick }) => {
  const getRiskBadge = () => {
    if (!tender.risk_score) return null;

    let className = styles.riskLow;
    let label = 'Низкий риск';

    if (tender.risk_score >= 0.7) {
      className = styles.riskHigh;
      label = 'Высокий риск';
    } else if (tender.risk_score >= 0.4) {
      className = styles.riskMedium;
      label = 'Средний риск';
    }

    return <span className={`${styles.riskBadge} ${className}`}>{label}</span>;
  };

  return (
    <div className={styles.card} onClick={onClick}>
      <div className={styles.header}>
        <div className={styles.number}>{tender.announce_number}</div>
        {getRiskBadge()}
      </div>

      <h3 className={styles.title}>{tender.name}</h3>

      <div className={styles.organizer}>
        <BiBuilding />
        <span>{tender.organizer_name}</span>
      </div>

      <div className={styles.footer}>
        <div className={styles.sum}>
          {(tender.total_sum / 1000000).toFixed(1)} млн ₸
        </div>
        <div className={styles.date}>
          {new Date(tender.publish_date).toLocaleDateString('ru-RU')}
        </div>
      </div>

      {tender.is_analyzed && (
        <div className={styles.analyzed}>
          <FiCheckCircle />
          <span>Проанализировано AI</span>
        </div>
      )}
    </div>
  );
};

export default TenderCard;