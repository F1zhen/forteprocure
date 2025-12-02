import { useState } from 'react';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import Header from './components/Header/Header';
import SearchBar from './components/SearchBar/SearchBar';
import UploadSection from './components/UploadSection/UploadSection';
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
      toast.warning('Введите хотя бы один параметр поиска');
      return;
    }

    setIsSearching(true);
    setTenders([]);
    setAnalysisData(null);

    try {
      const results = await searchTenders(keyword, dateFrom, dateTo);
      setTenders(results);
    } catch (error) {
      toast.error('Ошибка при поиске: ' + (error as Error).message);
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
      toast.error('Ошибка при анализе: ' + (error as Error).message);
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
      toast.error('Ошибка при загрузке файла: ' + (error as Error).message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSupplierCheck = async (bin: string) => {
    const res = await checkSupplierRisk(bin);
    return {
      bin: res.bin,
      is_risky: res.is_risky,
      registries: res.registries,
    };
  };

  const goBack = () => setAnalysisData(null);

  return (
    <div className={styles.app}>
      <Header />

      <div className={styles.container}>
        <SearchBar onSearch={handleSearch} isLoading={isSearching} />
        <UploadSection onUpload={handleFileUpload} isLoading={isUploading} />

        <EmptyState
          tenders={tenders}
          analysisData={analysisData}
          isSearching={isSearching}
          isAnalyzing={isAnalyzing}
          isUploading={isUploading}
          onTenderClick={handleTenderClick}
        />

        <div className={styles.supplierCheckSection}>
          <SupplierCheckSection onCheck={handleSupplierCheck} />
        </div>
      </div>

      <ToastContainer
        position="top-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
      />
    </div>
  );
}

export default App;