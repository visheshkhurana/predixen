import { type User, type InsertUser, type Scenario, type InsertScenario, type FinancialInput, type SimulationResult } from "@shared/schema";
import { randomUUID } from "crypto";

export interface IStorage {
  getUser(id: number): Promise<User | undefined>;
  getUserByEmail(email: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  
  getScenarios(): Promise<Scenario[]>;
  getScenario(id: string): Promise<Scenario | undefined>;
  createScenario(scenario: InsertScenario): Promise<Scenario>;
  updateScenario(id: string, scenario: Partial<InsertScenario>): Promise<Scenario | undefined>;
  deleteScenario(id: string): Promise<boolean>;
  
  getFinancialData(): Promise<FinancialInput | undefined>;
  saveFinancialData(data: FinancialInput): Promise<FinancialInput>;
  
  getLatestSimulation(): Promise<SimulationResult | undefined>;
  saveSimulation(result: SimulationResult): Promise<SimulationResult>;
}

export class MemStorage implements IStorage {
  private users: Map<number, User>;
  private scenarios: Map<string, Scenario>;
  private financialData: FinancialInput | undefined;
  private latestSimulation: SimulationResult | undefined;

  constructor() {
    this.users = new Map();
    this.scenarios = new Map();
    this.financialData = undefined;
    this.latestSimulation = undefined;
  }

  async getUser(id: number): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByEmail(email: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.email === email,
    );
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = this.users.size + 1;
    const user: User = { ...insertUser, id, created_at: new Date(), role: "user", is_active: true, updated_at: new Date(), oauth_provider: null, oauth_id: null, avatar_url: null, display_name: null, is_email_verified: false };
    this.users.set(id, user);
    return user;
  }

  async getScenarios(): Promise<Scenario[]> {
    return Array.from(this.scenarios.values());
  }

  async getScenario(id: string): Promise<Scenario | undefined> {
    return this.scenarios.get(id);
  }

  async createScenario(insertScenario: InsertScenario): Promise<Scenario> {
    const id = randomUUID();
    const scenario: Scenario = { ...insertScenario, id };
    this.scenarios.set(id, scenario);
    return scenario;
  }

  async updateScenario(id: string, update: Partial<InsertScenario>): Promise<Scenario | undefined> {
    const existing = this.scenarios.get(id);
    if (!existing) return undefined;
    const updated: Scenario = { ...existing, ...update };
    this.scenarios.set(id, updated);
    return updated;
  }

  async deleteScenario(id: string): Promise<boolean> {
    return this.scenarios.delete(id);
  }

  async getFinancialData(): Promise<FinancialInput | undefined> {
    return this.financialData;
  }

  async saveFinancialData(data: FinancialInput): Promise<FinancialInput> {
    this.financialData = data;
    return data;
  }

  async getLatestSimulation(): Promise<SimulationResult | undefined> {
    return this.latestSimulation;
  }

  async saveSimulation(result: SimulationResult): Promise<SimulationResult> {
    this.latestSimulation = result;
    return result;
  }
}

export const storage = new MemStorage();
