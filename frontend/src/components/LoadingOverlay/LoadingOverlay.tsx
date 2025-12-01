import React from 'react';
import styles from './LoadingOverlay.module.css';

interface LoadingOverlayProps {
  message?: string;
}

const LoadingOverlay: React.FC<LoadingOverlayProps> = ({ message = 'Загрузка...' }) => {
  return (
    <div className={styles.overlay}>
      <div className={styles.content}>
        <div className={styles.spinner}></div>
        <div className={styles.message}>{message}</div>
      </div>
    </div>
  );
};

export default LoadingOverlay;