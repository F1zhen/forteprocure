import React from 'react';
import { FiFileText } from 'react-icons/fi';
import styles from './Header.module.css';

const Header: React.FC = () => {
  return (
    <header className={styles.header}>
      <div className={styles.container}>
        <div className={styles.logo}>
          <div className={styles.logoIcon}>
            <FiFileText />
          </div>
          <div className={styles.logoText}>
            <h1>ForteProcure</h1>
            <p>Анализ тендеров и поиск рисков</p>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;