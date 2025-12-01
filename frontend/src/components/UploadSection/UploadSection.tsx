import React, { useRef } from 'react';
import { FiUpload } from 'react-icons/fi';
import styles from './UploadSection.module.css';

interface UploadSectionProps {
  onUpload: (file: File) => void;
  isLoading: boolean;
}

const UploadSection: React.FC<UploadSectionProps> = ({ onUpload, isLoading }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onUpload(file);
      // Reset input so same file can be uploaded again
      e.target.value = '';
    }
  };

  const handleClick = () => {
    if (!isLoading) {
      fileInputRef.current?.click();
    }
  };

  return (
    <div className={`${styles.uploadSection} ${isLoading ? styles.loading : ''}`}>
      <div className={styles.uploadIcon}>
        {isLoading ? (
          <div className={styles.spinner}></div>
        ) : (
          <FiUpload />
        )}
      </div>
      <div className={styles.uploadTitle}>
        {isLoading ? 'Анализируем документ...' : 'Загрузите документ тендера для анализа'}
      </div>
      <div className={styles.uploadSubtitle}>
        Поддерживаются форматы: PDF, DOCX
      </div>
      <button
        onClick={handleClick}
        className={styles.uploadButton}
        disabled={isLoading}
      >
        {isLoading ? 'Обработка...' : 'Выбрать файл'}
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx"
        onChange={handleFileChange}
        style={{ display: 'none' }}
        disabled={isLoading}
      />
    </div>
  );
};

export default UploadSection;