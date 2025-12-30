import { Routes, Route } from 'react-router-dom'
import Header from './components/Header'
import Organizations from './pages/Organizations'
import SubmissionForm from './pages/SubmissionForm'

function App() {
  return (
    <>
      <Header />
      
      {/* Navigation removed - now in sidebar */}

      {/* Routes */}
      <Routes>
        <Route path="/" element={<Organizations />} />
        <Route path="/submit" element={<SubmissionForm />} />
      </Routes>
    </>
  )
}

export default App
