import React from 'react';
import { FiSearch, FiFileText } from 'react-icons/fi';
import TenderCard from '../TenderCard/TenderCard';
import AnalysisView from '../AnalysisView/AnalysisView';
import { Tender, AnalysisData } from '../../types';
import styles from './EmptyState.module.css';

interface EmptyStateProps {
  tenders: Tender[];
  analysisData: AnalysisData | null;
  isSearching: boolean;
  isAnalyzing: boolean;
  isUploading: boolean;
  onTenderClick: (tender: Tender) => void;
}

const EmptyState: React.FC<EmptyStateProps> = ({
  tenders,
  analysisData,
  isSearching,
  isAnalyzing,
  isUploading,
  onTenderClick,
}) => {
  const renderLeftCard = () => {
    if (isSearching) {
      return (
        <div className={styles.loadingState}>
          <div className={styles.spinner}></div>
          <div className={styles.loadingText}>Поиск тендеров...</div>
        </div>
      );
    }

    if (tenders.length > 0) {
      return (
        <div className={styles.resultsContainer}>
          <div className={styles.resultsHeader}>
            <FiSearch />
            <span>Результаты поиска ({tenders.length})</span>
          </div>
          <div className={styles.resultsGrid}>
            {tenders.map(tender => (
              <TenderCard
                key={tender.id}
                tender={tender}
                onClick={() => onTenderClick(tender)}
              />
            ))}
          </div>
        </div>
      );
    }

    return (
      <div className={styles.card}>
        <div className={styles.icon}>
          <FiSearch />
        </div>
        <div className={styles.text}>
          Введите запрос и нажмите «Найти»
        </div>
      </div>
    );
  };

  const renderRightCard = () => {
    if (isAnalyzing || isUploading) {
      return (
        <div className={styles.loadingState}>
          <div className={styles.spinner}></div>
          <div className={styles.loadingText}>
            {isUploading ? 'Анализируем документ...' : 'Анализируем тендер...'}
          </div>
        </div>
      );
    }

    if (analysisData) {
      return (
        <div className={styles.analysisContainer}>
          <AnalysisView data={analysisData} />
        </div>
      );
    }

    return (
      <div className={styles.card}>
        <div className={styles.icon}>
          <FiFileText />
        </div>
        <div className={styles.text}>
          Выберите тендер из списка или загрузите документ для анализа
        </div>
      </div>
    );
  };

  return (
    <div className={styles.emptyState}>
      {renderLeftCard()}
      {renderRightCard()}
    </div>
  );
};

export default EmptyState;