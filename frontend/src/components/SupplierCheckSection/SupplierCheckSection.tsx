import React, { useState } from 'react';
import { FiSearch, FiAlertTriangle, FiCheckCircle, FiXCircle } from 'react-icons/fi';
import styles from './SupplierCheckSection.module.css';

interface SupplierRiskData {
  bin: string;
  is_risky: boolean;
  registries: Array<{
    source_registry: string;
    general_name?: string;
    first_name?: string;
    last_name?: string;
    middle_name?: string;
    external_id?: string;
    specialty_description?: string;
  }>;
}

interface SupplierCheckSectionProps {
  onCheck: (bin: string) => Promise<SupplierRiskData>;
}

const SupplierCheckSection: React.FC<SupplierCheckSectionProps> = ({ onCheck }) => {
  const [bin, setBin] = useState('');
  const [isChecking, setIsChecking] = useState(false);
  const [result, setResult] = useState<SupplierRiskData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCheck = async () => {
    if (!bin.trim()) {
      setError('Введите БИН/ИИН');
      return;
    }

    setIsChecking(true);
    setError(null);
    setResult(null);

    try {
      const data = await onCheck(bin.trim());
      setResult(data);
    } catch (err) {
      setError('Ошибка при проверке поставщика');
    } finally {
      setIsChecking(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isChecking) {
      handleCheck();
    }
  };

  return (
    <div className={styles.checkSection}>
      <div className={styles.header}>
        <h2 className={styles.title}>Проверка поставщиков</h2>
        <p className={styles.subtitle}>
          Проверьте поставщика в реестре недобросовестных участников
        </p>
      </div>

      <div className={styles.searchWrapper}>
        <input
          type="text"
          value={bin}
          onChange={(e) => setBin(e.target.value)}
          onKeyPress={handleKeyPress}
          className={styles.input}
          placeholder="Введите БИН/ИИН поставщика"
          disabled={isChecking}
        />
        <button
          onClick={handleCheck}
          className={styles.button}
          disabled={isChecking}
        >
          <FiSearch /> {isChecking ? 'Проверка...' : 'Проверить'}
        </button>
      </div>

      {error && (
        <div className={styles.error}>
          <FiAlertTriangle /> {error}
        </div>
      )}

      {isChecking && (
        <div className={styles.loading}>
          <div className={styles.spinner}></div>
          <p>Проверяем поставщика...</p>
        </div>
      )}

      {result && !isChecking && (
        <div className={styles.result}>
          {result.is_risky ? (
            <div className={styles.riskyResult}>
              <div className={styles.resultHeader}>
                <FiXCircle className={styles.riskyIcon} />
                <h3>Поставщик находится в реестре недобросовестных участников</h3>
              </div>
              <div className={styles.resultContent}>
                <div className={styles.binInfo}>БИН/ИИН: {result.bin}</div>
                {result.registries.map((registry, idx) => (
                  <div key={idx} className={styles.registryItem}>
                    {registry.general_name && (
                      <div className={styles.registryName}>{registry.general_name}</div>
                    )}
                    {(registry.first_name || registry.last_name) && (
                      <div className={styles.registryName}>
                        {registry.last_name} {registry.first_name} {registry.middle_name}
                      </div>
                    )}
                    <div className={styles.registryType}>
                      Реестр: {registry.source_registry}
                    </div>
                    {registry.specialty_description && (
                      <div className={styles.registryDescription}>
                        {registry.specialty_description}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className={styles.safeResult}>
              <div className={styles.resultHeader}>
                <FiCheckCircle className={styles.safeIcon} />
                <h3>Поставщик не найден в реестре недобросовестных участников</h3>
              </div>
              <div className={styles.resultContent}>
                <div className={styles.binInfo}>БИН/ИИН: {result.bin}</div>
                <p className={styles.safeMessage}>
                  Данный поставщик не числится в реестре недобросовестных участников государственных закупок.
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SupplierCheckSection;