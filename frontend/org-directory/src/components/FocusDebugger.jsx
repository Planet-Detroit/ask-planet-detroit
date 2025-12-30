// DEBUG COMPONENT - Add this temporarily to Organizations.jsx to see what focus values you have

import { useEffect, useState } from 'react'
import { supabase } from '../supabaseClient'

export default function FocusDebugger() {
  const [focusValues, setFocusValues] = useState([])
  
  useEffect(() => {
    async function checkFocus() {
      const { data } = await supabase
        .from('organizations')
        .select('focus')
        .eq('status', 'approved')
      
      const allFocus = new Set()
      data?.forEach(org => {
        org.focus?.forEach(f => {
          allFocus.add(`"${f}" (type: ${typeof f})`)
        })
      })
      setFocusValues(Array.from(allFocus).sort())
    }
    checkFocus()
  }, [])
  
  return (
    <div style={{ 
      position: 'fixed', 
      bottom: 20, 
      right: 20, 
      background: 'white', 
      padding: 20, 
      borderRadius: 8, 
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
      maxHeight: '400px',
      overflow: 'auto',
      zIndex: 9999,
      fontSize: '12px'
    }}>
      <h3 style={{ fontWeight: 'bold', marginBottom: 10 }}>Focus Values in Database:</h3>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {focusValues.map((val, i) => (
          <li key={i} style={{ marginBottom: 5 }}>{val}</li>
        ))}
      </ul>
    </div>
  )
}

// To use: Add to Organizations.jsx:
// import FocusDebugger from './FocusDebugger'
// Then add <FocusDebugger /> anywhere in the component's return
