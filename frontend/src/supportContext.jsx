import { createContext, useContext, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";

const SupportContext = createContext(null);

const initialAgentMessage = {
  id: "welcome",
  kind: "agent",
  text: "SupportPilot is ready. Ask a support question to begin.",
};

export function SupportProvider({ children }) {
  const [sessionId, setSessionId] = useState("shop-demo-1");
  const [customerId, setCustomerId] = useState("cust-001");
  const [status, setStatus] = useState("idle");
  const [handoffSummary, setHandoffSummary] = useState("");
  const [messages, setMessages] = useState([initialAgentMessage]);
  const [statusHistory, setStatusHistory] = useState([]);

  const apiBase = useMemo(() => {
    const isDev = window.location.port === "5173";
    return isDev ? "http://127.0.0.1:8000" : "";
  }, []);

  const appendMessage = (kind, text) => {
    setMessages((prev) => [...prev, { id: `${Date.now()}-${Math.random()}`, kind, text }]);
  };

  const callApi = async (path, payload) => {
    const res = await fetch(`${apiBase}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const msg = await res.text();
      throw new Error(msg || `Request failed with status ${res.status}`);
    }

    return res.json();
  };

  const applyAgentResponse = (data, fallbackStatus) => {
    appendMessage("agent", data.response || "(empty response)");
    const nextStatus = data.status || fallbackStatus;
    setStatus(nextStatus);
    setStatusHistory((prev) => [...prev, nextStatus]);
    setHandoffSummary(data.handoff_summary || "");
  };

  const chatMutation = useMutation({
    mutationFn: (payload) => callApi("/v1/chat/messages", payload),
    onSuccess: (data) => applyAgentResponse(data, "unknown"),
    onError: (error) => {
      appendMessage("agent", `Error: ${error.message}`);
      setStatus("error");
      setStatusHistory((prev) => [...prev, "error"]);
    },
  });

  const approveMutation = useMutation({
    mutationFn: (payload) => callApi("/v1/escalations/approve", payload),
    onSuccess: (data) => applyAgentResponse(data, "escalated"),
    onError: (error) => {
      appendMessage("agent", `Error: ${error.message}`);
      setStatus("error");
      setStatusHistory((prev) => [...prev, "error"]);
    },
  });

  const sendMessage = (text) => {
    const normalized = text.trim();
    if (!normalized || chatMutation.isPending) {
      return false;
    }

    appendMessage("user", normalized);
    chatMutation.mutate({
      session_id: sessionId.trim() || "shop-demo-1",
      customer_id: customerId.trim() || "cust-001",
      message: normalized,
    });
    return true;
  };

  const approveEscalation = () => {
    if (approveMutation.isPending) {
      return;
    }

    approveMutation.mutate({
      session_id: sessionId.trim() || "shop-demo-1",
      customer_id: customerId.trim() || "cust-001",
      message: "Human supervisor approved escalation.",
    });
  };

  const resetConversation = () => {
    setStatus("idle");
    setHandoffSummary("");
    setMessages([initialAgentMessage]);
    setStatusHistory([]);
  };

  const stats = useMemo(() => {
    const userMessages = messages.filter((m) => m.kind === "user").length;
    const agentMessages = messages.filter((m) => m.kind === "agent").length;
    const escalations = statusHistory.filter((s) => s === "escalated").length;
    const approvalsNeeded = statusHistory.filter((s) => s === "awaiting_human_approval").length;
    return {
      totalMessages: messages.length,
      userMessages,
      agentMessages,
      escalations,
      approvalsNeeded,
    };
  }, [messages, statusHistory]);

  const value = {
    apiBase,
    sessionId,
    setSessionId,
    customerId,
    setCustomerId,
    status,
    handoffSummary,
    messages,
    stats,
    canApprove: status === "awaiting_human_approval",
    isSending: chatMutation.isPending,
    isApproving: approveMutation.isPending,
    sendMessage,
    approveEscalation,
    resetConversation,
  };

  return <SupportContext.Provider value={value}>{children}</SupportContext.Provider>;
}

export function useSupport() {
  const context = useContext(SupportContext);
  if (!context) {
    throw new Error("useSupport must be used within SupportProvider");
  }
  return context;
}
