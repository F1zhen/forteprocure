import React, { useState } from 'react';
import { FiSearch } from 'react-icons/fi';
import styles from './SearchBar.module.css';

interface SearchBarProps {
  onSearch: (keyword: string, dateFrom: string, dateTo: string) => void;
  isLoading: boolean;
}

const SearchBar: React.FC<SearchBarProps> = ({ onSearch, isLoading }) => {
  const [keyword, setKeyword] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const handleSearch = () => {
    onSearch(keyword, dateFrom, dateTo);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      handleSearch();
    }
  };

  return (
    <div className={styles.searchSection}>
      <div className={styles.searchGrid}>
        <div className={styles.inputWrapper}>
          <label className={styles.label}>Поиск</label>
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyPress={handleKeyPress}
            className={styles.input}
            placeholder="Строительство, грунтовка, медицина..."
            disabled={isLoading}
          />
        </div>

        <div className={styles.inputWrapper}>
          <label className={styles.label}>Дата публикации (от)</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className={styles.input}
            disabled={isLoading}
          />
        </div>

        <div className={styles.inputWrapper}>
          <label className={styles.label}>Срок подачи (до)</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className={styles.input}
            disabled={isLoading}
          />
        </div>

        <button
          onClick={handleSearch}
          className={styles.button}
          disabled={isLoading}
        >
          <FiSearch /> {isLoading ? 'Поиск...' : 'Найти'}
        </button>
      </div>
    </div>
  );
};

export default SearchBar;