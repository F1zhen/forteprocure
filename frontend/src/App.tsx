// src/App.tsx
import { useState } from 'react';
import Header from './components/Header/Header';
import SearchBar from './components/SearchBar/SearchBar';
import UploadSection from './components/UploadSection/UploadSection';
import AnalysisView from './components/AnalysisView/AnalysisView';
import EmptyState from './components/EmptyState/EmptyState';
import SupplierCheckSection from './components/SupplierCheckSection/SupplierCheckSection';
import { searchTenders, analyzeTender, uploadTenderFile, checkSupplierRisk } from './services/api';
import { Tender, AnalysisData } from './types';
import styles from './App.module.css';

function App() {
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [analysisData, setAnalysisData] = useState<AnalysisData | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const handleSearch = async (keyword: string, dateFrom: string, dateTo: string) => {
    if (!keyword && !dateFrom && !dateTo) {
      alert('Введите хотя бы один параметр поиска');
      return;
    }

    setIsSearching(true);
    setTenders([]);
    setAnalysisData(null);

    try {
      const results = await searchTenders(keyword, dateFrom, dateTo);
      setTenders(results);
    } catch (error) {
      alert('Ошибка при поиске: ' + (error as Error).message);
    } finally {
      setIsSearching(false);
    }
  };

  const handleTenderClick = async (tender: Tender) => {
    setIsAnalyzing(true);
    try {
      const analysis = await analyzeTender(tender.id);
      setAnalysisData(analysis);
    } catch (error) {
      alert('Ошибка при анализе: ' + (error as Error).message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    setIsUploading(true);
    try {
      const result = await uploadTenderFile(file);
      const analysis = await analyzeTender(result.tender_id);
      setAnalysisData(analysis);
    } catch (error) {
      alert('Ошибка при загрузке файла: ' + (error as Error).message);
    } finally {
      setIsUploading(false);
    }
  };

  // Обёртка для проверки поставщика – убирает ошибку типов
  const handleSupplierCheck = async (bin: string) => {
    const res = await checkSupplierRisk(bin);
    return {
      bin: res.bin,
      is_risky: res.is_risky,
      registries: res.registries,
    };
  };

  const goBack = () => setAnalysisData(null);

  const isInAnalysisView = analysisData !== null;

  return (
    <div className={styles.app}>
      <Header />

      <div className={styles.container}>
        <SearchBar onSearch={handleSearch} isLoading={isSearching} />
        <UploadSection onUpload={handleFileUpload} isLoading={isUploading} />

        {/* Главное содержимое */}
        {isInAnalysisView ? (
          <>
            <button onClick={goBack} className={styles.backButton}>
              ← Назад к поиску
            </button>
            <AnalysisView data={analysisData} />
          </>
        ) : (
          <>
            {/* EmptyState теперь отвечает только за поиск и загрузку */}
            <EmptyState
              tenders={tenders}
              analysisData={null}
              isSearching={isSearching}
              isAnalyzing={isAnalyzing}
              isUploading={isUploading}
              onTenderClick={handleTenderClick}
            />

            {/* Проверка поставщика всегда видна в режиме поиска */}
            <div className={styles.supplierCheckSection}>
              <SupplierCheckSection onCheck={handleSupplierCheck} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default App;